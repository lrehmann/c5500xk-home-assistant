"""Binary sensors for Quantum Fiber ONT Bluetooth."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)

from .const import DOMAIN
from .entity import C5500XKEntity

DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="bluetooth_connection",
        name="Bluetooth connection",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="authenticated",
        name="Application authenticated",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="ethernet_wan_up",
        name="Ethernet WAN",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(key="sfp_present", name="SFP present"),
    BinarySensorEntityDescription(
        key="dsl_up", name="DSL interface", device_class=BinarySensorDeviceClass.CONNECTIVITY
    ),
    BinarySensorEntityDescription(
        key="atm_up", name="ATM interface", device_class=BinarySensorDeviceClass.CONNECTIVITY
    ),
    BinarySensorEntityDescription(
        key="ptm_up", name="PTM interface", device_class=BinarySensorDeviceClass.CONNECTIVITY
    ),
    BinarySensorEntityDescription(
        key="ethernet_1_status",
        name="Ethernet interface 1",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    BinarySensorEntityDescription(
        key="ethernet_2_status",
        name="Ethernet interface 2",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(C5500XKBinarySensor(coordinator, item) for item in DESCRIPTIONS)


class C5500XKBinarySensor(C5500XKEntity, BinarySensorEntity):
    def __init__(self, coordinator, description):
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self):
        if self.entity_key == "bluetooth_connection":
            return (
                self.coordinator.has_attempted_update
                and self.coordinator.last_update_success
            )
        value = self.coordinator.data.get(self.entity_key)
        return value if isinstance(value, bool) else str(value).lower() in {"1", "true", "up"}

    @property
    def available(self) -> bool:
        if self.entity_key == "bluetooth_connection":
            return True
        return super().available
