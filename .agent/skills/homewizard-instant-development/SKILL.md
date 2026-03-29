---
name: homewizard-instant-development
description: Repo-specific guidance for maintaining the WebSocket push behavior, sensors, and avoiding conflicts with the official integration
---

# HomeWizard Instant Development

This skill focuses on changes that must preserve the intent of this repository: **real-time push updates via the HomeWizard API v2 WebSocket** for P1 meters, while remaining safe and compatible with Home Assistant.

## When to Use

- You want to change data-update behavior or WebSocket handling
- You're modifying unique IDs / device registry behavior
- You're making changes that might conflict with the official HomeWizard integration
- You're adding or changing sensors

## Project Intent

- The official integration polls at a slower interval; this one connects to the **HomeWizard API v2 WebSocket** (`wss://<ip>/api/ws`) for real-time push updates.
- The domain is different (`homewizard_instant`) so it can run side-by-side with the official integration.
- IoT class is `local_push` — no polling interval is set.

## Architecture

```
config entry
    └── HWInstantCoordinator (DataUpdateCoordinator, no interval)
            ├── Initial REST fetch via HomeWizardEnergyV2 (HTTPS, Bearer token)
            │     GET /api         → DeviceV2
            │     GET /api/system  → SystemV2
            │     GET /api/measurement → MeasurementV2
            └── Background WebSocket task (wss://<ip>/api/ws)
                  → authenticate with Bearer token
                  → subscribe to "measurement"
                  → call async_set_updated_data() on each message
                  → reconnects automatically after 5 s on disconnect
```

## API v2 Authentication

- Token is generated once during onboarding via POST `/api/user` (requires physical button press on the P1 dongle).
- Token is stored in the config entry (`data["token"]`).
- Token is sent as `Authorization: Bearer <TOKEN>` on REST calls and as a WebSocket message `{"type": "authorization", "data": "<TOKEN>"}` on WS connect.
- All HTTPS calls use a permissive SSL context (self-signed HomeWizard cert).

## WebSocket Update Policy

- `DataUpdateCoordinator` is initialised with **no `update_interval`** — data arrives purely via push.
- `async_set_updated_data()` is called from `_handle_ws_message` for each incoming `measurement` message.
- Device and system data are only refreshed on coordinator restart (entry reload / HA restart).
- The WebSocket background task is cancelled via `entry.async_on_unload(coordinator._cancel_ws_task)`.

## Avoiding Conflicts with the Official Integration

- Device registry identifiers are prefixed with `homewizard_instant` in `entity.py`.
- Keep identifiers stable; changing them causes device/entity duplication for users.

## Adding New User-Facing Text

- Add text via `strings.json` and mirror to `translations/en.json` (they are kept identical).
- Prefer `translation_key` on entity descriptions over hardcoded names.

## Models

- All v2 data models live in `models.py` (no external library dependency).
- `DeviceResponseV2` is the coordinator's data type: `.device`, `.measurement`, `.system`.
- Sensor lambdas use `data.measurement.*` / `data.device.*` / `data.system.*`.

## Local Dev / Smoke Testing

- Use the VS Code task "Start Home Assistant" to run a dev instance.
- Watch logs for the `homewizard_instant` logger.

## Common "gotchas"

- Do not add REST calls inside the WebSocket message handler — it runs on every push event.
- Creating entities without `has_fn` leads to many entities showing unavailable.
- Raising raw exceptions instead of translation-aware `UpdateFailed` degrades UX.
- `self.ip_address` in the config flow can be `None` — always guard before passing to the API.
