"""Bluetooth coordinator for Quantum Fiber ONTs."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime

from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from homeassistant.components.bluetooth import (
    BluetoothCallbackMatcher,
    BluetoothScanningMode,
    async_discovered_service_info,
    async_last_service_info,
    async_register_callback,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ADVERTISEMENT_MAX_AGE,
    ADVERTISEMENT_REFRESH_COOLDOWN,
    ADVERTISEMENT_WAIT_SECONDS,
    AUTH_UUID,
    CONF_ADDRESS,
    CONF_SERIAL,
    CONNECTION_ATTEMPTS,
    CONNECTION_RETRY_DELAYS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    UUIDS,
)
from .protocol import build_auth_payload, decode_value, parse_advertisement_token

_LOGGER = logging.getLogger(__name__)
_CRITICAL_READS = ("pon_status", "rx_optical")


class C5500XKCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"C5500XK {entry.data[CONF_ADDRESS]}",
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.entry = entry
        self.address = entry.data[CONF_ADDRESS]
        self.serial = entry.data[CONF_SERIAL]
        self.data = {"serial": self.serial}
        self.has_attempted_update = False
        self._operation_lock = asyncio.Lock()
        self._advertisement_event = asyncio.Event()
        self._advertisement_refresh_task: asyncio.Task | None = None
        self._next_advertisement_refresh = 0.0
        self._store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self._service_info = self._find_latest_service_info()
        entry.async_on_unload(
            async_register_callback(
                hass,
                self._async_advertisement,
                BluetoothCallbackMatcher(local_name=self.serial, connectable=True),
                BluetoothScanningMode.ACTIVE,
            )
        )
        entry.async_on_unload(self._cancel_advertisement_refresh)

    def _find_latest_service_info(self):
        """Find this physical ONT even when its resolvable BLE address rotates."""
        matches = [
            info
            for info in async_discovered_service_info(self.hass, connectable=True)
            if info.name == self.serial
        ]
        if matches:
            return max(matches, key=lambda info: info.time)
        return async_last_service_info(self.hass, self.address, connectable=True)

    async def async_load_cache(self) -> None:
        """Restore the last successful values before the first Bluetooth attempt."""
        cached = await self._store.async_load()
        if not isinstance(cached, dict):
            return
        for key in ("last_success", "last_attempt"):
            if isinstance(cached.get(key), str):
                cached[key] = dt_util.parse_datetime(cached[key])
        self.data.update(cached)

    async def _async_save_cache(self, data: dict) -> None:
        """Persist successful readings so restarts do not erase known values."""
        cached = dict(data)
        for key in ("last_success", "last_attempt"):
            if isinstance(cached.get(key), datetime):
                cached[key] = cached[key].isoformat()
        await self._store.async_save(cached)

    def _async_advertisement(self, service_info, change) -> None:
        """Keep the current raw token and retry on each available connection window."""
        self._service_info = service_info
        self.address = service_info.address
        self._advertisement_event.set()
        if self._operation_lock.locked():
            return
        now = time.monotonic()
        if now < self._next_advertisement_refresh:
            return
        if (
            self._advertisement_refresh_task is not None
            and not self._advertisement_refresh_task.done()
        ):
            return
        self._next_advertisement_refresh = now + ADVERTISEMENT_REFRESH_COOLDOWN
        self._advertisement_refresh_task = self.entry.async_create_background_task(
            self.hass,
            self._async_refresh_from_advertisement(),
            f"C5500XK advertisement refresh {self.address}",
        )

    async def _async_refresh_from_advertisement(self) -> None:
        """Request a coordinator refresh without blocking the Bluetooth callback."""
        await self.async_request_refresh()

    def _cancel_advertisement_refresh(self) -> None:
        """Cancel an advertisement-triggered refresh when the entry unloads."""
        if (
            self._advertisement_refresh_task is not None
            and not self._advertisement_refresh_task.done()
        ):
            self._advertisement_refresh_task.cancel()

    async def _connection_inputs(self):
        service_info = self._service_info
        if (
            service_info is None
            or service_info.raw is None
            or time.monotonic() - service_info.time > ADVERTISEMENT_MAX_AGE
        ):
            self._advertisement_event.clear()
            try:
                async with asyncio.timeout(ADVERTISEMENT_WAIT_SECONDS):
                    await self._advertisement_event.wait()
            except TimeoutError as err:
                raise UpdateFailed("No fresh connectable advertisement received") from err
            service_info = self._service_info
        if service_info is None or service_info.raw is None:
            raise UpdateFailed("Fresh advertisement did not include raw data")
        token = parse_advertisement_token(service_info.raw)
        if (device := service_info.device) is None:
            raise UpdateFailed("Device is not currently available through a Bluetooth proxy")
        return device, token, service_info.rssi, service_info.source

    async def _connect_authenticated(self):
        device, token, rssi, source = await self._connection_inputs()
        client = await establish_connection(
            BleakClientWithServiceCache,
            device,
            self.serial,
            max_attempts=2,
            pair=True,
            use_services_cache=True,
        )
        try:
            await client.write_gatt_char(
                AUTH_UUID,
                build_auth_payload(self.serial, token),
                response=False,
            )
        except Exception:
            await client.disconnect()
            raise
        return client, rssi, source

    async def _async_update_data(self) -> dict:
        async with self._operation_lock:
            self.has_attempted_update = True
            self.data["last_attempt"] = datetime.now().astimezone()
            last_error: Exception | None = None
            for attempt in range(CONNECTION_ATTEMPTS):
                try:
                    client, rssi, source = await self._connect_authenticated()
                    try:
                        fresh, read_errors = {}, {}
                        read_order = (
                            *_CRITICAL_READS,
                            *(key for key in UUIDS if key not in _CRITICAL_READS),
                        )
                        for key in read_order:
                            try:
                                fresh[key] = decode_value(
                                    key, await client.read_gatt_char(UUIDS[key])
                                )
                            except Exception as err:
                                read_errors[key] = str(err)
                                _LOGGER.debug("Unable to read %s: %s", key, err)
                        if not all(key in fresh for key in _CRITICAL_READS):
                            first_error = next(iter(read_errors.values()), "no protected values")
                            raise UpdateFailed(
                                "Application authentication did not yield protected PON data: "
                                f"{first_error}"
                            )
                        now = datetime.now().astimezone()
                        data = dict(self.data)
                        data.update(
                            fresh,
                            rssi=rssi,
                            proxy=source,
                            last_attempt=now,
                            last_success=now,
                            authenticated=True,
                        )
                        await self._async_save_cache(data)
                        return data
                    finally:
                        await client.disconnect()
                except Exception as err:
                    last_error = err
                    _LOGGER.debug(
                        "C5500XK Bluetooth attempt %s/%s failed: %s",
                        attempt + 1,
                        CONNECTION_ATTEMPTS,
                        err,
                    )
                    if attempt < CONNECTION_ATTEMPTS - 1:
                        self._advertisement_event.clear()
                        try:
                            async with asyncio.timeout(CONNECTION_RETRY_DELAYS[attempt]):
                                await self._advertisement_event.wait()
                        except TimeoutError:
                            pass
            raise UpdateFailed(f"Bluetooth update failed after retries: {last_error}")

    async def async_write(self, writes: list[tuple[str, bytes]]) -> None:
        """Authenticate and perform an explicitly requested write sequence."""
        async with self._operation_lock:
            try:
                client, _, _ = await self._connect_authenticated()
                try:
                    for uuid, payload in writes:
                        await client.write_gatt_char(uuid, payload, response=False)
                finally:
                    await client.disconnect()
            except Exception as err:
                raise HomeAssistantError(f"Bluetooth write failed: {err}") from err
