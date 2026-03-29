# HomeWizard Instant (Home Assistant custom integration)

This is a custom integration for **HomeWizard P1 meters** that receives energy data in **real time** via the HomeWizard local API v2 WebSocket.

Home Assistant's official HomeWizard integration is documented here:
- https://www.home-assistant.io/integrations/homewizard/

## Why this exists

The official integration typically updates at a slower interval (commonly ~5 s). This custom integration connects to the **HomeWizard API v2 WebSocket** (`wss://<device-ip>/api/ws`) and receives push updates as soon as the device reports new data — no polling required.

Because this integration uses a different domain (`homewizard_instant`), it can run **side-by-side** with the official integration on the same device.

## Requirements

- HomeWizard P1 meter with firmware that supports **API v2** (firmware 6.00+).
- The device must be reachable on your local network.
- **Physical access** to the device is required during setup (see [Onboarding](#onboarding)).

## Installation

### Manual

1. Copy the folder `custom_components/homewizard_instant` into your Home Assistant config folder:
   - `<config>/custom_components/homewizard_instant`
2. Restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**.
4. Search for **HomeWizard Instant** and follow the steps.

### HACS

If you add this repository to HACS as a custom repository (category: **Integration**), HACS will install it under `custom_components/homewizard_instant`.

## Onboarding

The HomeWizard API v2 uses **Bearer token authentication**. Generating a token requires a one-time physical interaction with the P1 dongle — there is no need to enable anything in the HomeWizard app.

### Setup steps

1. Go to **Settings → Devices & services → Add integration** and search for **HomeWizard Instant**.
2. Enter the **IP address** of your P1 meter and click **Submit**.
3. The integration shows the **Authorize** screen. **Press the button on your P1 dongle once**, then click **Submit** within 30 seconds.
4. Home Assistant receives a token from the device and the setup completes automatically.

> The device gives you a 30-second window after the button press. If the window expires, the screen shows an error — just press the button again and re-submit.

### Zeroconf (automatic discovery)

If your P1 meter is discovered automatically via mDNS, you will first be asked to confirm the device, and then taken to the **Authorize** screen where the button press is required.

### Re-authentication

If the token is ever revoked (e.g. you reset the device or deleted the user via the HomeWizard app), Home Assistant will prompt for re-authentication. Press the button on the dongle again to generate a fresh token.

## Data updates

This integration uses the **HomeWizard API v2 WebSocket** (`wss://<ip>/api/ws`):

- On startup, device info, system info and the first measurement are fetched via HTTPS REST calls.
- A persistent WebSocket connection is then opened and `measurement` updates are received in real time as the device reports them (typically every 1 second for DSMR 5.0 meters).
- If the connection drops, the integration reconnects automatically after 5 seconds.
- The integration is classified as `local_push` — it does not poll.

## Supported devices

- HomeWizard **P1 meters** (product type `HWE-P1`) only.

## Supported sensors

- **Energy import / export** — total and per-tariff (kWh).
- **Active power** — total and per-phase (W).
- **Voltage** — total and per-phase (V).
- **Current** — total and per-phase (A).
- **Frequency** (Hz).
- **Apparent power**, **Reactive power**, **Power factor** — per phase (when reported).
- **Average demand** — 15-minute average power (W).
- **Peak demand** — current month peak (W).
- **Grid quality counters** — voltage sags/swells, power failures.
- **Meter metadata** — DSMR version, meter model, meter ID, tariff.
- **Device diagnostics** — firmware version, Wi-Fi SSID, Wi-Fi RSSI, uptime.
- **External meters** connected to the P1 port — gas, water, heat, warm water, inlet heat.

## Examples

- Add the **Active power** sensor to an Energy dashboard card for real-time consumption graphs.
- Use the **Energy import** sensor in the Home Assistant Energy dashboard for long-term tracking.
- Automate based on the **Active power** sensor to react instantly to changes in consumption.

## Troubleshooting

| Symptom | Solution |
|---|---|
| Button-press window expired during setup | Press the button again and re-submit immediately |
| Device unreachable | Confirm the IP address and that the device is powered and on the same network |
| Token rejected after device reset | Use re-authentication (Settings → Devices & services → Configure) |
| Sensor shows unavailable | Check the HA logs; the WebSocket reconnects automatically within 5 s |

## Known limitations

- Only **P1 meters** are supported; other HomeWizard devices are not supported.
- This integration does not register services or actions.
- The WebSocket delivers measurements at the meter's native reporting interval (1 s for DSMR 5.0, 10 s for older protocols).

## Migrating from v1.x

Version 2.0 uses the **HomeWizard API v2** instead of API v1. Existing config entries created with v1 of this integration need to be **removed and re-added**:

1. Go to **Settings → Devices & services**, find **HomeWizard Instant** and click **Delete**.
2. Add the integration again and follow the new onboarding steps (button press).

The `python-homewizard-energy` library is no longer required.

## Removal

1. Remove the integration from **Settings → Devices & services**.
2. If installed manually, delete `custom_components/homewizard_instant`.
3. If installed via HACS, remove the repository from HACS and restart Home Assistant.
