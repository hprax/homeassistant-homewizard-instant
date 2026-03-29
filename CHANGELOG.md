# Changelog

All notable changes to this project will be documented in this file.

## [2.0.1] - 2026-03-29

### Added
- Migrated to **HomeWizard API v2** — integration no longer depends on the `python-homewizard-energy` library.
- New `api.py`: thin HTTPS client for `/api`, `/api/system`, `/api/measurement`, and user creation (`/api/user`).
- New `models.py`: pure-Python dataclasses (`DeviceV2`, `SystemV2`, `MeasurementV2`, `ExternalDevice`, `ExternalDeviceType`) covering all P1 measurement fields.
- **WebSocket push updates** via `wss://<ip>/api/ws` — coordinator streams real-time measurement data instead of polling every second. IoT class changed to `local_push`.
- **Token-based onboarding**: new `authorize` config-flow step asks the user to press the physical button on the P1 dongle once to generate a Bearer token (no HomeWizard app interaction required).
- Re-authentication flow regenerates the token via the same button-press mechanism.

### Changed
- `manifest.json`: `iot_class` → `local_push`, `requirements` cleared, version `2.0.1`.
- `coordinator.py`: replaced `DataUpdateCoordinator` polling loop with a background WebSocket task; auto-reconnects after 5 s on disconnect.
- `config_flow.py`: removed dependency on `HomeWizardEnergyV1`; added `authorize` and `reauth_confirm` steps; added `None` guards on `ip_address` for mypy correctness.
- `strings.json` / `translations/en.json`: replaced `reauth_enable_api` / `api_disabled` strings with `authorize` and `reauth_confirm` button-press instructions.
- Updated `homewizard-instant-development` agent skill to reflect WebSocket architecture.

### Maintenance
- README rewritten to document v2 onboarding, WebSocket behaviour, and migration from v1.x.

## [1.0.1] - 2026-02-27

### Changed
- Improved discovery and config flow handling for existing devices, including IP update scenarios.
- Refined entity and sensor handling to improve integration stability and measurement accuracy.

### Testing
- Added regression coverage for config flow, entity behavior, and sensor updates.

## [1.0.0] - 2026-01-31

### Added
- Initial stable release of the HomeWizard Instant integration.
