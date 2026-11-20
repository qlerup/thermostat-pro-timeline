# Presence schedules and Away mode

## Choose the trigger

For a house-wide setback, open the settings gear and choose the Away tab. Select the people who count as home and enter the temperature to use when everyone is away. Test with one room before adding delays or enabling combinations.

For an occupied office, use the Presence sensor tab instead. Pair the office thermostat with its binary occupancy sensor. Choose the occupied target and separate entry and exit delays. A motion sensor measures occupancy, not identity. For a plan specific to one person, use named people and the advanced presence combinations.

## Configuration reference

- presence_sensor_enabled: true/false to configure per‑room presence.
- presence_sensors: { climate.living_room: binary_sensor.motion_living }.
- presence_sensor_temps: { climate.living_room: 21 } temperature when presence is ON.
- presence_sensor_delays: { climate.living_room: { on_s: 60, off_s: 300 } } delays in seconds.
- presence_sensor_delay_units: { climate.living_room: minutes } optional units; supports seconds | minutes.
- away:
	- enabled: true/false
	- target_c: 17 (target when nobody home)
	- persons: [ person.me, person.partner ]
	- advanced_enabled: true/false (combinations editor)
	- combos: object of enabled presence combinations (usually managed in UI)
	- delay_enabled, delay_value, delay_unit: optional delay before applying Away.
