# Boiler control (backend)

- boiler_enabled: true/false to turn on boiler tools in the editor/runtime.
- boiler_switch: switch.* or input_boolean.* to control the boiler/relay.
- boiler_switch_domain: switch | input_boolean (auto‑detected from entity id if omitted).
- boiler_rooms: [ climate.living_room, climate.kitchen ] or omit for all climate rooms.
- boiler_on_offset / boiler_off_offset: °C hysteresis relative to current target.
- boiler_temp_sensor: sensor.* to control boiler by its own temperature if desired.
- boiler_min_temp / boiler_max_temp: clamp when using boiler_temp_sensor.
- boiler_multi_enabled: true/false to enable per‑room boiler assignment.
- boiler_room_settings: per‑room mapping for multi‑boiler mode:
	- climate.living_room:
		- enabled: true/false
		- switch: switch.boiler_1 (or input_boolean.boiler_1)
		- switch_domain: switch | input_boolean (optional if entity id includes domain)
		- on_offset / off_offset: optional per‑room offsets (°C)
