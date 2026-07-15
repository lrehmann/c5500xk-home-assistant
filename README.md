# Quantum Fiber C5500XK Bluetooth for Home Assistant

A HACS custom integration that reads a Quantum Fiber C5500XK SmartNID through
Home Assistant Bluetooth. Connectable ESPHome Bluetooth proxies are supported;
the integration does not use an external Pi-hole collector.

The protocol mappings and validation evidence are documented separately in the
[C5500XK BLE research repository](https://github.com/lrehmann/c5500xk-ble-research).

## Behavior

- Authenticates locally to the C5500XK's proprietary Bluetooth GATT service.
- Preserves the last successful values when a Bluetooth connection is missed.
- Caches successful readings so known values survive a Home Assistant restart.
- Reports Bluetooth connection health separately from the retained readings.
- Retries failed connections three times and coalesces frequent advertisements.
- Uses fresh advertisements from Home Assistant's best available connectable
  Bluetooth source, including ESPHome proxies.
- Leaves every operational write button disabled unless explicitly enabled.

## Sensors

The integration exposes confirmed read-only values including:

- device serial number, device MAC address, hardware and software versions;
- WAN IPv4 address, WAN status, interface states and packet counters;
- PON state, FSAN, optical levels, counters, errors and discards;
- Bluetooth signal, proxy source, last attempt and last successful update;
- mapped ping diagnostic inputs and results.

Optical threshold sensors and all sensors with `Ping` in their name are disabled
by default. They can be enabled individually from the device's entity page.

## Installation with HACS

1. In HACS, open **Integrations** and choose **Custom repositories**.
2. Add `https://github.com/lrehmann/c5500xk-home-assistant` as an
   **Integration** repository.
3. Install **Quantum Fiber C5500XK Bluetooth** and restart Home Assistant.
4. Add the integration from **Settings > Devices & services**. If Bluetooth
   discovery does not appear, enter the advertised Bluetooth address and full
   C5500XK serial manually.

The ONT must be visible to a connectable Home Assistant Bluetooth adapter or an
active ESPHome Bluetooth proxy during a connection window.

## Operational writes

Reboot, factory reset, WAN lease renewal, PPP reset, and ping execution are
disabled by default. They are not required for monitoring. Enabling write
actions in the integration options does not execute an action; each disabled
button must also be enabled and pressed explicitly.

## Privacy

Do not include real device serial numbers, Bluetooth or device MAC addresses,
WAN addresses, FSAN values, or other customer identifiers in public issues.

## License

MIT
