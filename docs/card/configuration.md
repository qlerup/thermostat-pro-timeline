# Card configuration

For setup instructions and examples from the dashboard, browse the [feature guides](features/index.md).

## Rooms and basics

- entities: Array of room controls; each item is either a `climate.*` entity (default) or `input_number.*` when using room “input number mode”.
- title: Optional card title; defaults to a localized “Thermostat Timeline”.
- default_temp: Global default setpoint (°C/°F depending on `temp_unit`). Per‑room defaults can be shown via `per_room_defaults`.
- min_temp, max_temp: Card clamp for allowed temperatures.
- row_height: Row height in pixels (40–120).
- temp_unit: auto | C | F. When auto, the card detects preference and adapts.
- time_12h: auto | true | false. When auto, the card detects 12h/24h.
- time_source: browser | ha. Use local browser time or Home Assistant timezone for “now”.
- now_update_ms: UI update interval for the “now” line (default 60000).

## Editing and apply behavior

- auto_apply: true/false. Apply “now” setpoint automatically in the background.
- apply_on_edit: true/false. If edit affects current period, apply immediately.
- apply_on_default_change: true/false. If default changes current period, apply immediately.
- show_pause_button: true/false. Show Pause in header; pause suppresses all set_temperature.
- pause_sensor_enabled: true/false and pause_sensor_entity: binary_sensor.* to auto‑pause while on.

## Room names, merges, sensors

- labels: { climate.living_room: "Living" } to override display names.
- merges: { climate.living_room: [climate.living_room_aux] } to send the same setpoint to multiple thermostats.
- temp_sensors: { climate.living_room: sensor.living_temp } to show room temperature from a sensor instead of `climate.current_temperature`.
- show_room_temp: true/false to display the temperature bubble.
- turn_on: { climate.living_room: { enabled: true, order: before|after } } to send `climate.turn_on` before/after `climate.set_temperature`.

## Input number room mode

- room_use_input_number: internal editor flag; in YAML just put the `input_number.*` directly in entities to force input number mode per room.

## External room sensors and device Boost mode

Selecting an external room temperature sensor changes the room temperature shown
by the card. With boiler control disabled, this does not change the scheduled
target sent to the radiator thermostat. Timeline does not forward temperature
measurements into a thermostat's manufacturer-specific external-sensor input;
keep any device-specific automation that performs that transfer.

Device Boost mode is not a Timeline pause. A scheduled application can select a
supported `manual` or `hold` preset and send the scheduled temperature, interrupting
Boost. A thermostat's own five-minute Boost timeout does not change the saved
Timeline schedule. Pause Timeline while you want device-local control; the exact
Boost timeout remains the thermostat's responsibility.

## Room defaults and automatic control

Set a room default for the hours between scheduled blocks. For example, use 18 degrees as the default and add a 21-degree block from 06:00 to 09:00. At 09:00 the default applies again unless another block or override takes effect.

Use shared storage with **Auto-apply** to run the schedule while the dashboard is closed. Enable **Apply on edit** when an edit to the current period should also update the thermostat immediately. **Apply on default change** does the same when the current period uses the room default.
