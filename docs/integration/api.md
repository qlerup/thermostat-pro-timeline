# API endpoints (for tools/diagnostics)

All endpoints require Home Assistant auth and are provided by the integration:

- GET /api/thermostat_timeline/version — returns versions only (store/settings/colors/weekday/profile/backup)
- GET /api/thermostat_timeline/state?instance_id=<id> — returns full schedules, settings, colors and backup snapshot for the active or requested instance
