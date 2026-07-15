"""Quantum Fiber ONT Bluetooth integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_ADDRESS,
    CONF_ENTITY_DEFAULTS_APPLIED,
    CONF_SERIAL,
    DEFAULT_DISABLED_SENSOR_KEYS,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import C5500XKCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _normalize_entity_registry(hass, entry)
    coordinator = C5500XKCoordinator(hass, entry)
    await coordinator.async_load_cache()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    _remove_collector_entities(hass, coordinator.serial)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    entry.async_create_background_task(
        hass,
        coordinator.async_refresh(),
        f"Initial C5500XK Bluetooth refresh {coordinator.address}",
    )
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Remove the retired collector API settings while preserving device identity."""
    if entry.version > 6:
        return False
    data = dict(entry.data)
    if entry.version < 3:
        if CONF_ADDRESS not in entry.data or CONF_SERIAL not in entry.data:
            return False
        data = {CONF_ADDRESS: entry.data[CONF_ADDRESS], CONF_SERIAL: entry.data[CONF_SERIAL]}
    unique_id = entry.unique_id
    if entry.version < 6:
        serial = data[CONF_SERIAL]
        if not any(
            other.entry_id != entry.entry_id and other.unique_id == serial
            for other in hass.config_entries.async_entries(DOMAIN)
        ):
            unique_id = serial
    hass.config_entries.async_update_entry(
        entry,
        data=data,
        unique_id=unique_id,
        version=6,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def _remove_collector_entities(hass: HomeAssistant, identity: str) -> None:
    """Remove entities that existed only for the retired external collector."""
    registry = er.async_get(hass)
    for platform, key in (
        ("sensor", "collector"),
        ("sensor", "adapter"),
        ("sensor", "last_error"),
        ("binary_sensor", "writes_allowed"),
    ):
        if entity_id := registry.async_get_entity_id(platform, DOMAIN, f"{identity}_{key}"):
            registry.async_remove(entity_id)


def _normalize_entity_registry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Apply identity and default-enabled migrations after the registry is loaded."""
    registry = er.async_get(hass)
    address = entry.data[CONF_ADDRESS]
    serial = entry.data[CONF_SERIAL]
    old_prefix = f"{address}_"
    for registry_entry in list(registry.entities.values()):
        if (
            registry_entry.config_entry_id != entry.entry_id
            or not registry_entry.unique_id.startswith(old_prefix)
        ):
            continue
        suffix = registry_entry.unique_id.removeprefix(old_prefix)
        new_unique_id = f"{serial}_{suffix}"
        if registry.async_get_entity_id(
            registry_entry.domain, DOMAIN, new_unique_id
        ) is None:
            registry.async_update_entity(
                registry_entry.entity_id,
                new_unique_id=new_unique_id,
            )

    if entry.data.get(CONF_ENTITY_DEFAULTS_APPLIED):
        return
    for key in DEFAULT_DISABLED_SENSOR_KEYS:
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{serial}_{key}")
        if entity_id is None:
            continue
        registry_entry = registry.async_get(entity_id)
        if registry_entry is not None and registry_entry.disabled_by is None:
            registry.async_update_entity(
                entity_id,
                disabled_by=er.RegistryEntryDisabler.INTEGRATION,
            )
    data = dict(entry.data)
    data[CONF_ENTITY_DEFAULTS_APPLIED] = True
    hass.config_entries.async_update_entry(entry, data=data)
