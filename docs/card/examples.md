# Examples

## Richer card example

```yaml
type: custom:thermostat-timeline-card
title: Thermostat Pro Timeline
entities:
  - climate.living_room
  - climate.kitchen
default_temp: 20
min_temp: 5
max_temp: 25
row_height: 64
time_12h: auto
time_source: ha
auto_apply: true
apply_on_edit: true
apply_on_default_change: true
show_pause_button: true
show_room_temp: true
labels:
  climate.living_room: Living
merges:
  climate.living_room: [ climate.living_room_aux ]
temp_sensors:
  climate.living_room: sensor.living_temp
turn_on:
  climate.living_room: { enabled: true, order: before }
weekdays_enabled: true
weekdays_mode: weekday_weekend
profiles_enabled: true
presence_sensor_enabled: true
presence_sensors:
  climate.living_room: binary_sensor.motion_living
presence_sensor_temps:
  climate.living_room: 21
presence_sensor_delays:
  climate.living_room: { on_s: 60, off_s: 300 }
away:
  enabled: true
  persons: [ person.me ]
  target_c: 17
open_window:
  enabled: true
  sensors:
    climate.living_room: [ binary_sensor.window_living ]
  open_delay_min: 2
  close_delay_min: 5
boiler_enabled: true
boiler_switch: switch.boiler
boiler_on_offset: 0.5
boiler_off_offset: 0.5
color_global: true
color_ranges:
  "*":
    - { from: 5, to: 18, color: "#4da3ff" }
    - { from: 18, to: 21, color: "#ffd166" }
    - { from: 21, to: 26, color: "#ff7f50" }
storage_enabled: true
instance_enabled: true
instance_id: winter
backup_auto_enabled: true
backup_interval_days: 7
```
