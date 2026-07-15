# Quantum Fiber SmartNID Bluetooth for Home Assistant

A HACS custom integration that reads Quantum Fiber C5500XK and C6500XK
SmartNIDs through Home Assistant Bluetooth. Connectable ESPHome Bluetooth
proxies are supported; the integration does not use an external Pi-hole
collector.

The protocol mappings and validation evidence are documented separately in the
[C5500XK BLE research repository](https://github.com/lrehmann/c5500xk-ble-research).

> [!IMPORTANT]
> C5500XK support was validated against a real device. C6500XK support is an
> experimental compatibility profile added without access to C6500XK hardware
> or firmware. The integration recognizes its serial-shaped local name and
> attempts the C5500XK pairing, authentication, and protected-read sequence,
> but that proprietary protocol has not been confirmed on a C6500XK. The
> integration only marks authentication successful after protected PON values
> are returned. Operational writes are blocked for C6500XK devices.

## Behavior

- Recognizes full `C5500XK...` and `C6500XK...` advertised serials.
- Pairs through Home Assistant's selected connectable Bluetooth source and uses
  the full advertised serial in the application-authentication calculation.
- Authenticates locally to the verified C5500XK proprietary Bluetooth GATT
  service and attempts the same protocol profile for experimental C6500XK
  support.
- Preserves the last successful values when a Bluetooth connection is missed.
- Caches successful readings so known values survive a Home Assistant restart.
- Reports Bluetooth connection health separately from the retained readings.
- Retries failed connections three times and coalesces frequent advertisements.
- Follows the advertised device serial across resolvable Bluetooth address
  rotation instead of pinning the ONT to one transient MAC address.
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
3. Install **Quantum Fiber SmartNID Bluetooth** and restart Home Assistant.
4. Add the integration from **Settings > Devices & services**. If Bluetooth
   discovery does not appear, enter the advertised Bluetooth address and full
   C5500XK or C6500XK serial manually.

The ONT must be visible to a connectable Home Assistant Bluetooth adapter or an
active ESPHome Bluetooth proxy during a connection window.

Older manual installations may contain duplicate device entries created when a
resolvable Bluetooth address changed. Keep the entry for the intended ONT
serial and remove duplicate entries for that same serial before upgrading.

## Operational writes

On verified C5500XK devices, reboot, factory reset, WAN lease renewal, PPP
reset, and ping execution are disabled by default. They are not required for
monitoring. Enabling write actions in the integration options does not execute
an action; each disabled button must also be enabled and pressed explicitly.
These operational writes are blocked in code for experimental C6500XK devices.

## C6500XK validation boundary

Public primary sources confirm that the C6500XK is a Gemtek Quantum Fiber
SmartNID with Bluetooth 5.1 Low Energy. They do not publish its Bluetooth local
name, manufacturer-data format, proprietary GATT UUIDs, or application-auth
construction. Until a real C6500XK returns protected telemetry, its support is
not considered verified. See the
[C6500XK compatibility research](https://github.com/lrehmann/c5500xk-ble-research/blob/main/docs/c6500xk-compatibility.md)
for the evidence and required capture procedure.

## Privacy

Do not include real device serial numbers, Bluetooth or device MAC addresses,
WAN addresses, FSAN values, or other customer identifiers in public issues.

## License

MIT
