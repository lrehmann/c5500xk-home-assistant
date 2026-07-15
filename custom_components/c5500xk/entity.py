"""Base entity for Quantum Fiber ONT Bluetooth."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class C5500XKEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key: str) -> None:
        super().__init__(coordinator)
        self.entity_key = key
        self._attr_unique_id = f"{coordinator.serial}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata, including versions learned after setup."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.serial)},
            name="Quantum Fiber C5500XK",
            manufacturer="Gemtek Technology Co., Ltd.",
            model="C5500XK",
            serial_number=(self.coordinator.data or {}).get("serial"),
            sw_version=(self.coordinator.data or {}).get("software_version"),
            hw_version=(self.coordinator.data or {}).get("hardware_version"),
        )

    @property
    def available(self) -> bool:
        """Keep the last known value available during transient BLE failures."""
        return self.entity_key in self.coordinator.data
