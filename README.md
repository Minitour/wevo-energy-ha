# Wevo Energy Home Assistant Integration

Custom Home Assistant integration for Wevo Energy chargers.

## Features
- UI setup flow (email + password login)
- Discovers chargers available to the account and lets user choose
- Automatic token refresh (no manual token replacement when access token expires)
- Authorize charging button
- Current charging state sensor
- Current charging speed sensor (kW)
- Session energy sensor (kWh)
- Monthly energy sensor (kWh) – sum of all sessions in the current calendar month

## Project structure
- `custom_components/wevo_energy/` – Home Assistant custom component

## Install (manual)
1. Copy `custom_components/wevo_energy` into your HA config `custom_components` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Wevo Energy**.
4. Log in with Wevo account credentials, then select charger.

## Entities
- `button.wevo_authorize_charging`
- `sensor.wevo_charging_state`
- `sensor.wevo_charging_speed`
- `sensor.wevo_session_energy`
- `sensor.wevo_monthly_energy`

## Notes
- Cognito defaults are preconfigured based on observed Wevo app behavior:
  - Region: `eu-central-1`
  - Client ID: `2amm11et52j39kubdekse641b6`
- These are editable in setup in case Wevo changes auth settings.
