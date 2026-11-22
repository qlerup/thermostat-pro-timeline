"""Opt-in fan schedules and presence profiles for individual Timeline rooms."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_UPDATED
from .thermal import celsius, numeric

_LOGGER = logging.getLogger(__name__)


def clock_minute(value):
    try:
        hour, minute = map(int, value.split(":"))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return hour * 60 + minute
    except (AttributeError, ValueError):
        pass
    return None


def night_time(rule, minute):
    start, end = clock_minute(rule.get("night_start", "22:00")), clock_minute(rule.get("night_end", "07:00"))
    if not rule.get("night") or None in (start, end) or start == end:
        return False
    return start <= minute < end if start < end else minute >= start or minute < end


def adjustment(rule, profile, mode, base, indoor=None):
    """Signed Celsius difference from the current block and permission for its fan boost."""
    if mode not in ("heat", "cool"):
        return 0, True
    if profile in ("eco", "alarm_eco"):
        amount = numeric(rule.get("eco_delta", 0)) or 0
        return (amount if mode == "cool" else -amount), True
    if profile not in ("comfort", "night"):
        return 0, True
    amount = numeric(rule.get("night_delta", 0) if profile == "night" else rule.get("boost", 1)) or 0
    delta = -amount if mode == "cool" else amount
    limit = numeric(rule.get("cap"))
    if limit is not None and delta > 0 and (base + delta > limit or (indoor is not None and indoor >= limit)):
        action = rule.get("cap_action", "clamp")
        if action == "clamp":
            return (0 if indoor is not None and indoor >= limit else max(0, limit - base)), True
        return 0, action == "fan_only"
    return delta, True


def choose_speed(rule, block, gap, target, profile, allow_fan, quiet):
    speed = rule.get("default_speed", "")
    for field, value in (("targets", target), ("smart", gap)):
        if value is None:
            continue
        matches = [(numeric(r.get("at")), r.get("speed")) for r in rule.get(field, []) if isinstance(r, dict)]
        options = [(n, s) for n, s in matches if n is not None and s and value >= n]
        if options:
            speed = max(options, key=lambda row: row[0])[1]
    speed = block.get("fan_speed") or speed
    if allow_fan:
        speed = rule.get(profile + "_speed") or speed
    if quiet:
        speed = rule.get("night_speed") or speed
    return speed


class RoomAir:
    def __init__(self, hass, entry, managers):
        self.hass, self.entry, self.managers = hass, entry, managers
        self.store = Store(hass, 1, DOMAIN + ".room_air", atomic_writes=True)
        self.log, self.held, self.baselines = {}, {}, {}
        self.stable, self.dwell, self.sent, self.status = {}, {}, {}, {}
        self.intent = {}
        self.treatment_commands = {}
        self.recovering = set()
        self.task = None
        self.dirty = self.write = False

    def snapshot(self, iid, room=None):
        rooms = self.status.get(iid, {})
        if room:
            return {**rooms.get(room, {}), "history": self.log.get(iid + "/" + room, [])}
        return {room: {k: v for k, v in status.items() if k != "history"} for room, status in rooms.items()}

    async def load(self):
        data = await self.store.async_load() or {}
        self.log, self.held, self.baselines = (data.get(k, {}) for k in ("log", "held", "baselines"))
        self.recovering = set(self.held)

    def start(self):
        self.entry.async_on_unload(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self.wake))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.wake, timedelta(seconds=5)))
        self.entry.async_on_unload(self.close)
        self.wake()

    def close(self):
        if self.task:
            self.task.cancel()

    @callback
    def wake(self, *_):
        self.dirty = True
        if self.task is None or self.task.done():
            self.task = self.entry.async_create_background_task(
                self.hass, self.run(), "Timeline room air", eager_start=False
            )

    async def save(self):
        await self.store.async_save({"log": self.log, "held": self.held, "baselines": self.baselines})
        self.write = False

    async def run(self):
        while self.dirty:
            self.dirty = False
            try:
                await self.update()
                if self.write:
                    await self.save()
            except Exception:
                _LOGGER.exception("Room air update failed")

    def profile(self, key, rule, minute, now):
        if not rule.get("presence"):
            self.stable.pop(key, None)
            return "schedule", "Normal schedule"
        alarm = rule.get("alarm")
        if alarm:
            state = self.hass.states.get(alarm)
            if not state or state.state in ("armed_away", "unknown", "unavailable"):
                self.stable.pop(key, None)
                return ("alarm_eco" if rule.get("alarm_eco") else "alarm"), "Presence ignored: alarm " + (
                    state.state if state else "unavailable"
                )
        selected = rule.get("profile", "automatic")
        if selected in ("comfort", "eco", "night", "schedule"):
            return selected, "Selected profile: " + selected
        state = self.hass.states.get(rule.get("sensor", ""))
        if not state or state.state not in ("on", "off"):
            self.stable.pop(key, None)
            return "schedule", "Presence sensor unavailable"
        delay = int(rule.get("on_s" if state.state == "on" else "off_s", 30 if state.state == "on" else 120))
        age = (now - state.last_changed).total_seconds()
        if age >= delay:
            self.stable[key] = rule.get("sensor"), state.state
        sensor, stable = self.stable.get(key, (None, None))
        if sensor != rule.get("sensor"):
            stable = None
        if stable == "on":
            limit = rule.get("boost_minutes", 0)
            if limit and state.state == "on" and age >= delay + limit * 60:
                return "schedule", "Comfort duration expired"
            if night_time(rule, minute):
                return "night", "Night profile: occupied"
            return "comfort", f"Comfort: presence detected for {rule.get('on_s', 30)} s"
        if stable == "off":
            return "eco", f"Eco: room empty for {rule.get('off_s', 120)} s"
        return "schedule", "Waiting for stable presence"

    async def call(self, domain, service, entity, **fields):
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **fields}, blocking=True)

    async def speed(self, key, entity, requested, enforce):
        """Restore the previous fan setting only when our last command still owns it."""
        baseline = self.baselines.get(key)
        if baseline and baseline["entity"] != entity:
            await self.speed(key, baseline["entity"], "", False)
            if key in self.baselines:
                return
        state = self.hass.states.get(entity) if entity else None
        if not state or state.state in ("unknown", "unavailable"):
            return
        a = state.attributes
        climate = entity.startswith("climate.")
        if not climate and not entity.startswith("fan."):
            return
        current = (
            a.get("fan_mode")
            if climate
            else (
                "off"
                if state.state == "off"
                else a.get("preset_mode") or str(a.get("percentage") or 100) + "%"
            )
        )
        baseline = self.baselines.get(key)
        restoring = not requested
        if restoring:
            self.intent.pop(key, None)
            if not baseline:
                return
            requested = baseline.get("before") if current == baseline["last"] else None
            if not requested or current == requested:
                self.baselines.pop(key, None)
                self.write = True
                return
        if climate and state.state == "off":
            return
        if not restoring and current == requested:
            self.intent[key] = (entity, requested)
            return
        if not restoring and not enforce and self.intent.get(key) == (entity, requested):
            return
        if climate and requested in a.get("fan_modes", []):
            domain, service, fields = "climate", "set_fan_mode", {"fan_mode": requested}
        elif not climate and requested == "off":
            domain, service, fields = "fan", "turn_off", {}
        elif not climate and requested in (a.get("preset_modes") or []):
            domain, service, fields = (
                "fan",
                "turn_on" if state.state == "off" else "set_preset_mode",
                {"preset_mode": requested},
            )
        elif (
            not climate
            and requested.endswith("%")
            and (value := numeric(requested[:-1])) is not None
            and 0 < value <= 100
        ):
            domain, service, fields = "fan", "set_percentage", {"percentage": round(value)}
        else:
            if restoring:
                self.baselines.pop(key, None)
                self.write = True
            return
        await self.call(domain, service, entity, **fields)
        if restoring:
            self.baselines.pop(key, None)
        else:
            self.intent[key] = (entity, requested)
            self.baselines[key] = {
                "entity": entity,
                "before": baseline["before"] if baseline else current,
                "last": requested,
            }
        self.write = True

    async def humidity(self, key, entity, requested, enforce):
        base = self.baselines.get(key)
        if base and base["entity"] != entity:
            await self.humidity(key, base["entity"], None, False)
            if key in self.baselines:
                return
            base = None
        if not entity or not entity.startswith("humidifier."):
            return
        st = self.hass.states.get(entity)
        if not st or st.state in ("unknown", "unavailable"):
            return
        current = st.attributes.get("humidity")
        if requested is None:
            self.intent.pop(key, None)
            if base and current == base["last"] and base["before"] is not None:
                await self.call("humidifier", "set_humidity", entity, humidity=base["before"])
            if base:
                self.baselines.pop(key)
                self.write = True
            return
        if st.state != "on" or not st.attributes.get("min_humidity", 0) <= requested <= st.attributes.get(
            "max_humidity", 100
        ):
            return
        if current != requested and (enforce or self.intent.get(key) != (entity, requested)):
            await self.call("humidifier", "set_humidity", entity, humidity=requested)
            self.baselines[key] = {
                "entity": entity,
                "before": base["before"] if base else current,
                "last": requested,
            }
            self.write = True
        self.intent[key] = (entity, requested)

    async def update(self):
        iid = self.hass.data[DOMAIN].get("active_instance_id") or "default"
        mgr = self.managers.get(iid)
        if not mgr:
            return
        schedules, settings = mgr._get_data()
        rules = settings.get("air_rooms") or {}
        now = dt_util.now()
        minute = now.hour * 60 + now.minute
        status = {}
        # Build a complete snapshot before replacing the one dashboards are reading.
        for room, row in schedules.items():
            key = iid + "/" + room
            rule = rules.get(room) or {}
            if (
                not any(
                    rule.get(k) for k in ("fans", "presence", "season", "stop", "enforce", "night", "air", "treatment")
                )
                and key not in self.held
                and not any(key + s in self.baselines for s in ("/fan", "/air", "/humidity"))
                and key not in self.sent
            ):
                continue
            try:
                await self.room(mgr, settings, schedules, room, row, key, rule, now, minute, status)
            except Exception:
                _LOGGER.exception("Room air control failed for %s", room)
        self.status = {iid: status}

    async def room(self, mgr, settings, schedules, room, row, key, r, now, minute, status):
        state = self.hass.states.get(room)
        if not state or state.state in ("unavailable", "unknown"):
            return
        profile, reason = self.profile(key, r, minute, now)
        person = mgr._room_person(settings, room)
        person_state = self.hass.states.get(person) if person else None
        if (
            not profile.startswith("alarm")
            and person_state
            and person_state.state not in ("home", "unknown", "unavailable", "")
        ):
            profile, reason = "schedule", "Assigned person away"
        alarm = profile.startswith("alarm")
        hold = (settings.get("room_pause") or {}).get(room) or {}
        window = mgr._owd_mgr()
        paused = (
            not mgr._auto_apply_enabled()
            or not (settings.get("apply_enabled") or {}).get(room, True)
            or mgr._room_control_paused(settings, room)
            or hold.get("indef")
            or (hold.get("until_ms") or 0) > now.timestamp() * 1000
            or mgr._summer_off(room, settings)
            or (window and window.is_entity_suspended(room))
        )
        if paused:
            getattr(mgr, "_air_context", {}).pop(room, None)
            self.dwell.pop(key, None)
            self.publish(
                key,
                room,
                status,
                profile if alarm else "paused",
                reason if alarm else "Schedule paused",
                None,
                now,
            )
            return
        if (r.get("treatment") and not settings.get("pause_indef")
                and (settings.get("pause_until_ms") or 0) <= now.timestamp() * 1000
                and not mgr._pause_sensor_on(settings) and not mgr._alarm_paused(self.hass, settings)):
            await self.treat_air(mgr, settings, room, key, r, now)
        block = next(
            (
                b
                for b in mgr._effective_blocks_today(row, settings, room)
                if int(b.get("startMin", -1)) <= minute < int(b.get("endMin", -1))
            ),
            {},
        )
        blockmode = mgr._block_mode(room, schedules, settings, minute)
        mode = blockmode or self.held.get(key) or state.state
        if mode == "temperature_only":
            mode = state.state
        base = mgr._desired_for(room, schedules, settings, minute, air_profile=False)
        if base is None:
            return
        base_c = mgr._stored_setpoint_c(base, settings)
        source = (settings.get("temp_sensors") or {}).get(room) or room
        thermal = self.hass.data[DOMAIN].get("thermal")
        indoor = thermal.reading(source) if thermal else None
        delta, allow_fan = adjustment(r, profile, mode, base_c, indoor)
        mgr._air_context = getattr(mgr, "_air_context", {})
        mgr._air_context[room] = (profile, mode, indoor)
        desired = mgr._desired_for(room, schedules, settings, minute)
        target = mgr._stored_setpoint_c(desired, settings)
        error = None if indoor is None else (indoor - target if mode == "cool" else target - indoor)
        held = self.held.get(key)
        tolerance = r.get("band", 0.2)
        if held:
            release = (
                not r.get("stop")
                or blockmode not in (None, held)
                or (error is not None and error > tolerance + r.get("restart_gap", 0.3))
            )
            if key not in self.recovering and state.state not in ("off", held):
                release = True
            if release:
                if (
                    (state.state == "off" or (key in self.recovering and state.state != (blockmode or held)))
                    and blockmode not in ("off", "temperature_only")
                    and (blockmode or held) in state.attributes.get("hvac_modes", [])
                ):
                    await self.call("climate", "set_hvac_mode", room, hvac_mode=blockmode or held)
                self.held.pop(key, None)
                self.write = True
            elif state.state != "off":
                await self.call("climate", "set_hvac_mode", room, hvac_mode="off")
            self.recovering.discard(key)
        elif (
            r.get("stop")
            and room.startswith("climate.")
            and state.state in ("heat", "cool")
            and mode == state.state
            and blockmode != "temperature_only"
            and "off" in state.attributes.get("hvac_modes", [])
            and error is not None
            and error <= tolerance
        ):
            # A changed target or HVAC mode starts a new dwell interval.
            identity = (mode, target)
            last, since = self.dwell.get(key, (None, 0))
            if last != identity:
                since = now.timestamp()
                self.dwell[key] = identity, since
            if now.timestamp() - since >= r.get("stop_minutes", 5) * 60:
                self.held[key] = mode
                self.dwell.pop(key, None)
                await self.save()
                await self.call("climate", "set_hvac_mode", room, hvac_mode="off")
        else:
            self.dwell.pop(key, None)
        command = (target, blockmode, profile)
        previous = self.sent.get(key)
        actual = celsius(state.attributes.get("temperature"), self.hass.config.units.temperature_unit)
        device_target = (
            mgr._clamp_climate_setpoint_c(target, state.attributes, mgr._ha_uses_fahrenheit())
            if actual is not None
            else None
        )
        mismatch = blockmode not in (None, "temperature_only", state.state) or (
            blockmode not in ("off", "fan_only", "dry")
            and actual is not None
            and abs(actual - device_target) > 0.05
        )
        if key not in self.held and (
            (command != previous and (previous is not None or delta or blockmode))
            or (r.get("enforce") and mismatch)
            or (held and key not in self.held)
        ):
            for entity in [room, *(settings.get("merges") or {}).get(room, [])]:
                await mgr.async_apply_entity_now(entity, reconcile=True)
        self.sent[key] = command
        speed = ""
        fan = r.get("fan") or room
        if (
            r.get("fans")
            and (fan != room or (state.state != "off" and key not in self.held))
            and blockmode != "off"
        ):
            speed = choose_speed(
                r,
                block,
                None if error is None else max(0, error),
                target,
                profile,
                allow_fan,
                night_time(r, minute),
            )
        await self.speed(key + "/fan", fan, speed, r.get("enforce", False))
        air = r.get("air_entity") or ""
        if r.get("presence") and r.get("air") and air and air != fan:
            device = self.hass.states.get(air)
            if air.startswith("fan.") and device and not (
                r.get("treatment") and r.get("purify_device") == air and device.state == "off"
            ):
                air_speed = r.get("air_" + profile) if profile != "alarm" else ""
                await self.speed(key + "/air", air, air_speed or "", r.get("enforce", False))
        else:
            await self.speed(key + "/air", air, "", False)
        humidity_entity = r.get("humidity_entity") if r.get("presence") and r.get("air") else None
        await self.humidity(
            key + "/humidity", humidity_entity, r.get("humidity_" + profile), r.get("enforce", False)
        )
        if reason == "Normal schedule" and night_time(r, minute):
            reason = "Quiet hours"
        if key in self.held:
            reason += " Â· Off at target"
        self.publish(key, room, status, profile, reason, speed, now)
        device = self.hass.states.get(fan) if r.get("fans") else None
        if device:
            attrs = device.attributes
            status[room]["current_speed"] = (
                attrs.get("fan_mode")
                if fan.startswith("climate.")
                else "off"
                if device.state == "off"
                else attrs.get("preset_mode")
                or (str(attrs["percentage"]) + "%" if attrs.get("percentage") is not None else None)
            )
        if not any(r.get(k) for k in ("fans", "presence", "season", "stop", "enforce", "night", "air", "treatment")):
            self.sent.pop(key, None)
            mgr._air_context.pop(room, None)

    async def treat_air(self, mgr, settings, room, key, rule, now):
        """Apply each device's hysteresis and confirm transitions from HA feedback."""
        for kind, label, domain, default_on, default_off in (
            ("purify", "Air purifier", "fan", 20, 15),
            ("dry", "Dehumidifier", "humidifier", 60, 55),
            ("mist", "Humidifier", "humidifier", 40, 45),
        ):
            entity = rule.get(kind + "_device") or ""
            sensor = self.hass.states.get(rule.get(kind + "_sensor")) if rule.get(kind + "_sensor") else None
            if not entity.startswith(domain + ".") or not sensor:
                continue
            device = self.hass.states.get(entity)
            if not device or device.state not in ("on", "off"):
                continue
            if kind in ("dry", "mist") and rule.get("dry_device") == rule.get("mist_device"):
                continue
            value = numeric(sensor.state)
            start = numeric(rule.get(kind + "_start", default_on))
            stop = numeric(rule.get(kind + "_stop", default_off))
            if None in (value, start, stop) or (start >= stop if kind == "mist" else start <= stop):
                continue
            command_key = (key, kind)
            pending = self.treatment_commands.get(command_key)
            if pending and pending[0] == entity and device.state == pending[1]:
                self.treatment_commands.pop(command_key)
                message = pending[3]
                self.log.setdefault(key, []).append({"at": now.isoformat(), "reason": message})
                del self.log[key][:-50]
                self.write = True
                notifications = settings.get("pause_notifications") or {}
                if notifications.get("enabled") is not False and notifications.get("treatment"):
                    await mgr._send_pause_notification(notifications, message)
            demand = value <= start if kind == "mist" else value >= start
            clear = value >= stop if kind == "mist" else value <= stop
            desired = "on" if demand else "off" if clear else None
            if desired is None or desired == device.state:
                continue
            if pending and pending[:2] == (entity, desired) and now.timestamp() - pending[2] < 60:
                continue
            name = (settings.get("labels") or {}).get(room) or room
            unit = sensor.attributes.get("unit_of_measurement", "")
            change = "started" if demand else "stopped"
            message = f"{name}: {label} {change} ({sensor.name}: {value:g} {unit})."
            await self.call(domain, "turn_" + desired, entity)
            self.treatment_commands[command_key] = (entity, desired, now.timestamp(), message)

    def publish(self, key, room, status, profile, reason, speed, now):
        fact = {"profile": profile, "reason": reason, "speed": speed or None}
        history = self.log.setdefault(key, [])
        if not history or any(history[-1].get(k) != v for k, v in fact.items()):
            history.append({**fact, "at": now.isoformat()})
            del history[:-50]
            self.write = True
        status[room] = {**fact, "history": history}
