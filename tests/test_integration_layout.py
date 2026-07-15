"""Static safety and packaging checks for the HACS integration."""

import json
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_manifest_uses_home_assistant_bluetooth() -> None:
    manifest = json.loads((ROOT / "custom_components/c5500xk/manifest.json").read_text())
    assert manifest["dependencies"] == ["bluetooth"]
    assert manifest["bluetooth"] == [{"local_name": "C5500XK*", "connectable": True}]


def test_hacs_integration_has_no_external_collector() -> None:
    assert not (ROOT / "collector").exists()
    assert not (ROOT / "custom_components/c5500xk/api.py").exists()


def test_operational_buttons_default_disabled() -> None:
    source = (ROOT / "custom_components/c5500xk/button.py").read_text()
    assert "_attr_entity_registry_enabled_default = False" in source
    assert "CONF_ENABLE_WRITES" in source


def test_stale_values_remain_available() -> None:
    source = (ROOT / "custom_components/c5500xk/entity.py").read_text()
    assert "return self.entity_key in self.coordinator.data" in source
    assert "super().available and" not in source


def test_connection_retries_are_bounded() -> None:
    source = (ROOT / "custom_components/c5500xk/coordinator.py").read_text()
    constants = (ROOT / "custom_components/c5500xk/const.py").read_text()
    assert "for attempt in range(CONNECTION_ATTEMPTS)" in source
    assert "CONNECTION_ATTEMPTS = 3" in constants
    assert "ADVERTISEMENT_REFRESH_COOLDOWN = 15" in constants
    assert "entry.async_on_unload(self._cancel_advertisement_refresh)" in source


def test_rotating_addresses_are_matched_by_serial() -> None:
    source = (ROOT / "custom_components/c5500xk/coordinator.py").read_text()
    entity_source = (ROOT / "custom_components/c5500xk/entity.py").read_text()
    flow_source = (ROOT / "custom_components/c5500xk/config_flow.py").read_text()
    assert "BluetoothCallbackMatcher(local_name=self.serial" in source
    assert "async_discovered_service_info" in source
    assert 'f"{coordinator.serial}_{key}"' in entity_source
    assert "await self.async_set_unique_id(serial)" in flow_source


def test_wan_identity_and_diagnostics_are_mapped() -> None:
    constants = (ROOT / "custom_components/c5500xk/const.py").read_text()
    sensors = (ROOT / "custom_components/c5500xk/sensor.py").read_text()
    for key in ("serial", "device_mac", "wan_ipv4", "ping_host", "ping_repetitions"):
        assert f'"{key}"' in constants
        assert f'key="{key}"' in sensors


def test_threshold_and_ping_sensors_default_disabled() -> None:
    source = (ROOT / "custom_components/c5500xk/sensor.py").read_text()
    blocks = source.split("C5500XKSensorDescription(")[1:]
    matching = [block for block in blocks if 'name="Ping' in block or "threshold" in block]
    assert len(matching) == 13
    assert all("entity_registry_enabled_default=False" in block for block in matching)


def test_existing_threshold_and_ping_sensors_are_migrated_disabled() -> None:
    init_source = (ROOT / "custom_components/c5500xk/__init__.py").read_text()
    flow_source = (ROOT / "custom_components/c5500xk/config_flow.py").read_text()
    assert "DEFAULT_DISABLED_SENSOR_KEYS" in init_source
    assert "RegistryEntryDisabler.INTEGRATION" in init_source
    assert "VERSION = 6" in flow_source
    assert "_normalize_entity_registry(hass, entry)" in init_source


def test_standalone_hacs_metadata() -> None:
    manifest = json.loads((ROOT / "custom_components/c5500xk/manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    assert manifest["documentation"].endswith("/c5500xk-home-assistant")
    assert manifest["version"] == "0.3.3"
    assert hacs["name"] == "Quantum Fiber C5500XK Bluetooth"
