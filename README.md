# ❄️ Thermostat Pro Timeline — Integration + Card
[![hacs\_badge](https://img.shields.io/badge/HACS-Default-blue.svg)](https://hacs.xyz) [![Downloads](https://img.shields.io/github/downloads/qlerup/thermostat-pro-timeline/total)](https://github.com/qlerup/thermostat-pro-timeline/releases)

## Support this project

If you find this project useful, you can support me on Ko-fi 💙  

[![Buy me some debugging time on Ko-fi](https://img.shields.io/badge/%F0%9F%90%9E_Buy_me_some_debugging_time_on-Ko--fi-2ea44f?style=for-the-badge)](https://ko-fi.com/qlerup)


## 📝 Overview

Thermostat Pro Timeline is a Home Assistant solution composed of:

- A custom integration (`thermostat_timeline`) that provides a shared schedules store, background control, backup/restore, and a small HTTP API used by the card.
- A Lovelace card (`custom:thermostat-pro-timeline`) for visual 24‑hour timeline planning, with advanced features like weekdays, profiles, presence and holidays.


<img width="2288" height="476" alt="image" src="https://github.com/user-attachments/assets/95a17e9d-e404-4bad-ba93-5af0a6cff6d5" />

## Highlights (Features)

- 🗓️ **Timeline planner for multiple rooms**: Drag, resize, and double-click to edit heating/cooling periods for each room.
- 📅 **Per-weekday schedules**: Two timeline views (all rooms for one day, or all days for one room). Supports weekday grouping (weekday/weekend, Sat/Sun, or all 7 days).
- 🏷️ **Profiles**: Named day schedules per room, with quick activate/deactivate and full profile management from the card.
- 👥 **Presence schedules**: Advanced “who’s home” logic, per-person selection, presence sensors, and Away mode with delays and combinations.
- 🎉 **Holidays**: Separate schedule for holidays, with support for calendar entities or manual date lists.
- ⚡ **Auto-apply setpoint**: Instantly applies setpoint to `climate.*` or `input_number.*` at “now”; can also auto-apply on edit or default changes.
- ⏸️ **Global Pause**: Pause all automation via a button or binary sensor; suppresses all set_temperature commands.
- 🌡️ **Room temperature bubble**: Shows current temperature per room, with optional override sensor per room.
- ➕ **Merge thermostats**: Merge multiple thermostats under one room line; supports `turn_on` sequencing (before/after setpoint).
- 🪟 **Open Window Detection (OWD)**: Turns off rooms when window/door sensors are open, with configurable open/close delays.
- 🔥 **Boiler control**: Control a boiler (switch or input_boolean) with hysteresis, min/max limits, and optional boiler temperature sensor. Assign rooms, offsets, and domain.
- 🎨 **Color ranges**: Custom color palettes for heat/cool blocks, per-room or global. Full color mapping for temperature intervals.
- 🗄️ **Shared, multi-user storage**: File-based storage in the integration; no helper sensor required. Multi-user and multi-dashboard safe.
- 🗂️ **Multi-instance support**: Separate schedules/settings by `instance_id` (e.g., “winter”, “summer”); switch or rename via services.
- 💾 **Backup/restore**: Built-in backup/restore with multiple slots, partial section selection, and automatic backup intervals.
- 🚀 **Automatic resource install**: Integration copies/updates the JS card to `/local` and registers the Lovelace resource (with cache-busting).
- 🔢 **Input number mode**: Use `input_number.*` entities as room controls instead of climate entities.
- 🏷️ **Labels and merges**: Override room display names and merge multiple thermostats for unified control.
- ▶️ **Turn on sequencing**: Optionally send `climate.turn_on` before/after `set_temperature` per room.
- 🏠 **Per-room defaults**: Show and manage default temperatures per room.
- 🔄 **Weekdays view switch**: Toggle between timeline browsing modes in the card header.
- ⏱️ **Presence sensor delays and units**: Configure on/off delays and units (seconds/minutes) for presence sensors.
- 🏡 **Away mode combinations**: Advanced editor for presence/away combinations and delays.
- 📆 **Holiday sources**: Use calendar entities or manual date lists for holidays.
- 🏢 **Boiler room assignment**: Assign boiler control to specific rooms or all climate rooms.
- 📉 **Boiler temperature clamp**: Clamp boiler operation by min/max temperature when using a boiler temp sensor.
- 🕒 **Storage sync modes**: Choose instant or delayed storage sync, with configurable batching.
- 🌍 **Internationalization**: Fully localized card with auto-detection and support for 12+ languages.
- 🛠️ **API endpoints**: HTTP API for diagnostics, versioning, and state export.
- 🚫 **No helper entity needed**: All storage is handled by the integration; no need for extra sensors or helpers.
- 🕹️ **Background control**: Thermostats update even when the card is closed, as long as storage is enabled.
- 👨‍👩‍👧‍👦 **Multi-user safe**: Shared storage and sync for all dashboards and users.

## 🌍 Localization

| Language       | Supported |
| -------------- | --------- |
| 🇩🇰 Danish    | ✅         |
| 🇸🇪 Swedish   | ✅         |
| 🇳🇴 Norwegian | ✅         |
| 🇬🇧 English   | ✅         |
| 🇩🇪 German    | ✅         |
| 🇪🇸 Spanish   | ✅         |
| 🇫🇷 French    | ✅         |
| 🇫🇮 Finnish   | ✅         |
| 🇨🇿 Czech     | ✅         |

## 📚 Contents

- 🛠️ Installation
- ⚡ Quick start (minimal YAML)
- 🧩 Card configuration (full YAML options)
- 🛎️ Integration services (YAML examples)
- 🌍 Internationalization (languages and detection)
- 🛠️ API endpoints (for tools/diagnostics)
- 🧩 Tips & troubleshooting




## 🛠️ Installation

**Prerequisites:** Home Assistant Core, Lovelace dashboards.

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=qlerup&repository=thermostat-pro-timeline)

### 🛒 Option A — HACS (Recommended)

1. 🏠 Go to HACS in Home Assistant.
2. ⚙️ Click on "Integrations" and select "Custom repositories" (gear icon in the top right corner).
3. ➕ Add the following repository URL and select "Integration" as type.
   ```yaml
   https://github.com/qlerup/lovelace-thermostat-pro-timeline
      ```
4. 🔍 Find and install the "Thermostat Pro Timeline" integration from the HACS list.
5. 🔄 Restart Home Assistant.
6. 📦 The integration will automatically copy the card (JS file) to `/local` and register it as a Lovelace resource.

### 📦 Option B — Manual installation

1. ⬇️ Download the integration from GitHub: [qlerup/thermostat-pro-timeline](https://github.com/qlerup/thermostat-pro-timeline).
2. 📁 Copy the `thermostat_timeline` folder to `custom_components/` in your Home Assistant config directory:
   - Location: `custom_components/thermostat_timeline/`
3. 🗂️ Copy the file `thermostat-pro-timeline.js` to the `www/` folder in your Home Assistant config:
   - Location: `www/thermostat-pro-timeline.js` (accessed as `/local/thermostat-pro-timeline.js`)
4. 🔄 Restart Home Assistant.
5. 📝 If you use YAML dashboards, add the resource manually under "resources" in Lovelace:
   ```yaml
   resources:
     - url: /local/thermostat-pro-timeline.js
       type: module
   ```
6. 🗃️ If you use storage dashboards, the integration will handle the resource and cache-busting automatically.

**ℹ️ Note:**
- 🧹 If the resource is missing: Reload your browser cache. Make sure the resource is added correctly.
- 🔄 Storage dashboards: The integration automatically updates the resource with cache-busting.
- 📝 YAML dashboards: Add the resource manually as shown above.


## ⚡ Quick start (minimal YAML)

Add the card to any dashboard view:

```yaml
type: custom:thermostat-pro-timeline
title: Heating timeline
entities:
	- climate.living_room
	- climate.kitchen
default_temp: 20
min_temp: 5
max_temp: 25
```


## 🧩 Card configuration (full YAML options)

Rooms and basics

- entities: Array of room controls; each item is either a `climate.*` entity (default) or `input_number.*` when using room “input number mode”.
- title: Optional card title; defaults to a localized “Thermostat Timeline”.
- default_temp: Global default setpoint (°C/°F depending on `temp_unit`). Per‑room defaults can be shown via `per_room_defaults`.
- min_temp, max_temp: Card clamp for allowed temperatures.
- row_height: Row height in pixels (40–120).
- temp_unit: auto | C | F. When auto, the card detects preference and adapts.
- time_12h: auto | true | false. When auto, the card detects 12h/24h.
- time_source: browser | ha. Use local browser time or Home Assistant timezone for “now”.
- now_update_ms: UI update interval for the “now” line (default 60000).

Editing and apply behavior

- auto_apply: true/false. Apply “now” setpoint automatically in the background.
- apply_on_edit: true/false. If edit affects current period, apply immediately.
- apply_on_default_change: true/false. If default changes current period, apply immediately.
- show_pause_button: true/false. Show Pause in header; pause suppresses all set_temperature.
- pause_sensor_enabled: true/false and pause_sensor_entity: binary_sensor.* to auto‑pause while on.

Room names, merges, sensors

- labels: { climate.living_room: "Living" } to override display names.
- merges: { climate.living_room: [climate.living_room_aux] } to send the same setpoint to multiple thermostats.
- temp_sensors: { climate.living_room: sensor.living_temp } to show room temperature from a sensor instead of `climate.current_temperature`.
- show_room_temp: true/false to display the temperature bubble.
- turn_on: { climate.living_room: { enabled: true, order: before|after } } to send `climate.turn_on` before/after `climate.set_temperature`.

Input number room mode

- room_use_input_number: internal editor flag; in YAML just put the `input_number.*` directly in entities to force input number mode per room.

Weekdays

- weekdays_enabled: true/false to enable weekday schedules.
- weekdays_mode: weekday_weekend | weekday_sat_sun | all_7 to choose day groupings.
- weekdays_view: all_rooms_one_day | one_room_all_days to pick timeline browsing mode.
- weekdays_view_switch_in_timeline: true to show a toggle in the main header.

Profiles (named overrides per room)

- profiles_enabled: true/false to allow per‑room named day schedules. Profiles are created and managed from the card’s Profiles dialog.

Presence schedules and Away

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

Holidays

- holidays_enabled: true/false
- holidays_source: calendar | manual
- holidays_entity: calendar.* or a binary sensor that is on during holidays
- holidays_dates: [ "YYYY-MM-DD", ... ] manual date list when using manual source

Open Window Detection (OWD)

- open_window:
	- enabled: true/false
	- sensors: { climate.living_room: [ binary_sensor.window_living, binary_sensor.door_balcony ] }
	- open_delay_min: minutes to wait before turning off when open
	- close_delay_min: minutes to wait before resuming when closed

Boiler control (frontend‑side)

- boiler_enabled: true/false to turn on boiler tools in the editor/runtime.
- boiler_switch: switch.* or input_boolean.* to control the boiler/relay.
- boiler_switch_domain: switch | input_boolean (auto‑detected from entity id if omitted).
- boiler_rooms: [ climate.living_room, climate.kitchen ] or omit for all climate rooms.
- boiler_on_offset / boiler_off_offset: °C hysteresis relative to current target.
- boiler_temp_sensor: sensor.* to control boiler by its own temperature if desired.
- boiler_min_temp / boiler_max_temp: clamp when using boiler_temp_sensor.

Color ranges

- color_global: true/false (use a single palette for all rooms when true)
- color_ranges: mapping of room or `*` to intervals:

```yaml
color_global: true
color_ranges:
	"*":
		- { from: 5, to: 18, color: "#4da3ff" }
		- { from: 18, to: 21, color: "#ffd166" }
		- { from: 21, to: 26, color: "#ff7f50" }
```

Shared storage, sync, backup

- storage_enabled: true/false. Default on. Uses file‑based storage via the integration; no helper sensor entity needed.
- instance_enabled: true to keep separate schedules/settings by `instance_id`.
- instance_id: free text (normalized to safe id) — e.g. winter, summer.
- storage_sync_mode: instant | delay (delay batches writes)
- storage_sync_min / storage_sync_sec: delay config if `storage_sync_mode: delay` (min/sec).
- backup_auto_enabled: true/false and backup_interval_days: 1..365 for automatic backups.

Example: a richer card

```yaml
type: custom:thermostat-pro-timeline
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


## 🛎️ Integration services (YAML examples)

All services live under the domain `thermostat_timeline`. You can call them from Developer Tools → Services or in automations/scripts.

Service: `set_store` — replace full store (optionally for an instance)

```yaml
service: thermostat_timeline.set_store
data:
	instance_id: winter
	activate: true
	schedules:
		climate.living_room:
			defaultTemp: 20
			blocks:
				- { from: "06:00", to: "08:00", temp: 21 }
	settings:
		min_temp: 5
		max_temp: 25
		labels: { climate.living_room: "Living" }
```

Service: `patch_entity` — merge into a single entity

```yaml
service: thermostat_timeline.patch_entity
data:
	entity_id: climate.kitchen
	data:
		defaultTemp: 21
		blocks:
			- { from: "17:00", to: "22:00", temp: 22 }
```

Service: `select_instance` — make an instance active (create/copy if needed)

```yaml
service: thermostat_timeline.select_instance
data:
	instance_id: summer
	create_if_missing: true
	copy_from_active: true
```

Service: `rename_instance`

```yaml
service: thermostat_timeline.rename_instance
data:
	old_instance_id: winter
	new_instance_id: heating_2026
```

Service: `backup_now` — create backup; choose sections

```yaml
service: thermostat_timeline.backup_now
data:
	main: true
	weekday: true
	presence: true
	settings: true
	holiday: true
	colors: true
```

Service: `restore_now` — restore backup; merge or replace and choose sections

```yaml
service: thermostat_timeline.restore_now
data:
	mode: merge
	main: true
	weekday: true
	presence: false
	settings: true
	holiday: false
	colors: true
```

Utilities

- `clear`: Clear all schedules and bump version.
- `factory_reset`: Delete integration storage files and recreate empty (removes all instances, schedules, settings, backups).


## 🌍 Internationalization (languages and detection)

The card is localized and auto‑selects language by:

1) `hass.locale.language` or `hass.language` from Home Assistant
2) Browser `navigator.language`
3) Fallback: English

Normalization: underscores are converted to hyphens and lower‑cased (e.g., da_DK → da-dk). Aliases map `no → nb`, `cz → cs`, `dk → da`.

Included languages

- English (en)
- Danish (da)
- Swedish (sv)
- Norwegian Bokmål (nb)
- German (de)
- Spanish (es)
- French (fr)
- Italian (it)
- Finnish (fi)
- Czech (cs)
- Slovenian (sl)


## 🛠️ API endpoints (for tools/diagnostics)

All endpoints require Home Assistant auth and are provided by the integration:

- GET /api/thermostat_timeline/version — returns versions only (store/settings/colors/weekday/profile/backup)
- GET /api/thermostat_timeline/state?instance_id=<id> — returns full schedules, settings, colors and backup snapshot for the active or requested instance


## 🧩 Tips & troubleshooting

- Resource missing: If the card isn’t found, reload the browser cache. In YAML dashboards, ensure the resource is declared with type: module and url: /local/thermostat-pro-timeline.js.
- No helper entity needed: Storage is file‑based via the integration; keep `storage_enabled: true` unless you intentionally prefer purely local (per‑browser) storage.
- Background control: With storage enabled, thermostats update even when the card is closed. Without it, commands are sent only while a card is open on a device.
- Multi‑instance: Enable `instance_enabled: true` and set a distinct `instance_id` per card or switch globally via `select_instance`.


## 🏅 License & credits

- Code owner: @qlerup
- Issues & docs: https://github.com/qlerup/thermostat-pro-timeline

