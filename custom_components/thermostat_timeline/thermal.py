"""Per-room learning from completed heating/cooling runs and percentage valve control."""

from __future__ import annotations

import logging
import math
from collections import Counter
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN, SIGNAL_UPDATED

_LOGGER = logging.getLogger(__name__)


def numeric(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def retention_days(rule):
    days = rule.get("days", 7)
    return days if type(days) is int and days > 0 else 7


def celsius(value, unit):
    value = numeric(value)
    if value is None or unit not in ("°C", "°F", "K"):
        return None
    if unit == "°F":
        return (value - 32) / 1.8
    return value - 273.15 if unit == "K" else value


def estimate(samples, mode, indoor, outdoor, target):
    """Distance-weighted nearest neighbours on indoor and outdoor starting temperatures."""
    neighbours = sorted(
        (
            (abs(s["indoor"] - indoor) + abs(s["outdoor"] - outdoor) / 3, s["pace"])
            for s in samples
            if s["mode"] == mode
        ),
        key=lambda item: item[0],
    )[:5]
    if len(neighbours) < 3:
        return None
    weights = [1 / (1 + distance) for distance, _ in neighbours]
    pace = sum(weight * sample[1] for weight, sample in zip(weights, neighbours)) / sum(weights)
    return math.ceil(abs(target - indoor) * pace)


def valve_position(error, mode, current, step):
    if mode == "proportional":
        # A two-degree proportional band. Quantize to a value the device accepts.
        if error <= 0:
            return 0
        if error >= 2:
            return 100
        return min(100, max(0, round(error * 50 / step) * step))
    if error >= 0.3:
        return 100
    if error <= 0:
        return 0
    return 100 if current == 100 else 0


class ThermalControl:
    def __init__(self, hass, entry, managers):
        self.hass, self.entry, self.managers = hass, entry, managers
        self.store = Store(hass, 1, DOMAIN + ".thermal_history", atomic_writes=True)
        self.save_needed = False
        self.retention = {}
        self.history = {}
        self.runs = {}
        self.candidates = {}
        self.previous_outdoor = {}
        self.status = {}
        self.active_manager = None
        self.task = None
        self.dirty = False

    async def start(self):
        saved = await self.store.async_load() or {}
        self.history = saved.get("history", saved)
        self.runs = saved.get("runs", {})
        self.retention = saved.get("retention_days", {})
        self.entry.async_on_unload(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self.wake))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.wake, timedelta(seconds=30)))
        self.entry.async_on_unload(self.close)
        self.wake()

    def close(self):
        if self.task:
            self.task.cancel()

    @callback
    def wake(self, *_):
        self.dirty = True
        if not self.task or self.task.done():
            self.task = self.entry.async_create_background_task(
                self.hass, self.run(), "Timeline room control", eager_start=False
            )

    async def run(self):
        while self.dirty:
            self.dirty = False
            previous_runs = {k: dict(v) for k, v in self.runs.items()}
            try:
                await self.update()
            except Exception:
                _LOGGER.exception("Room learning or valve control failed")
            if self.runs != previous_runs:
                self.save_needed = True
            if self.save_needed:
                try:
                    await self.store.async_save(
                        {"history": self.history, "runs": self.runs, "retention_days": self.retention}
                    )
                    self.save_needed = False
                except OSError:
                    _LOGGER.exception("Could not save room learning data; will retry on the next update")

    def room_data(self, instance, room):
        key = instance + "/" + room
        return {
            "completed": self.history.get(key, []),
            "in_progress": self.runs.get(key),
            "retention_days": self.retention.get(key),
        }

    def reading(self, entity):
        state = self.hass.states.get(entity) if entity else None
        if not state or state.state in ("unknown", "unavailable"):
            return None
        if entity.startswith("weather."):
            return celsius(state.attributes.get("temperature"), state.attributes.get("temperature_unit"))
        if entity.startswith("climate."):
            return celsius(
                state.attributes.get("current_temperature"), self.hass.config.units.temperature_unit
            )
        return celsius(state.state, state.attributes.get("unit_of_measurement"))

    def observe(self, key, samples, now, mode, indoor, outdoor, target, action):
        sign = 1 if mode == "heat" else -1
        run = self.runs.get(key)
        if run and (
            run["mode"] != mode
            or run["target"] != target
            or now - run["last"] > 120
            or now - run["start"] > 21600
        ):
            self.runs.pop(key)
            run = None
        if run:
            if now - run["last"] >= 15:
                run["last"] = now
            duration = (now - run["start"]) / 60
            gain = sign * (indoor - run["indoor"])
            if sign * (target - indoor) <= 0.2 or action == "idle":
                if 3 <= duration <= 360 and gain >= 0.3:
                    samples.append(
                        dict(
                            at=now,
                            minutes=duration,
                            end_indoor=indoor,
                            target=target,
                            mode=mode,
                            indoor=run["indoor"],
                            outdoor=run["outdoor"],
                            pace=duration / gain,
                        )
                    )
                    self.save_needed = True
                self.runs.pop(key)
            return
        if action in (None, "heating" if mode == "heat" else "cooling") and sign * (target - indoor) >= 0.3:
            self.runs[key] = dict(
                start=now, last=now, mode=mode, target=target, indoor=indoor, outdoor=outdoor
            )

    def early_block(
        self,
        key,
        manager,
        room,
        schedules,
        settings,
        minute,
        now,
        indoor,
        outdoor,
        mode,
        samples,
        old,
        status,
    ):
        blocks = manager._effective_blocks_today(schedules[room], settings, room)
        upcoming = []
        for block in blocks:
            if not isinstance(block, dict):
                continue
            start = numeric(block.get("startMin"))
            end = numeric(block.get("endMin"))
            if start is not None and end is not None and minute < start <= minute + 180 and end > start:
                upcoming.append((int(start), block))
        if not upcoming:
            self.candidates.pop(key, None)
            return None
        start, block = min(upcoming, key=lambda pair: pair[0])
        future_mode = manager._block_mode(room, schedules, settings, start)
        current_mode = manager._block_mode(room, schedules, settings, minute)
        target = manager._desired_for(room, schedules, settings, start, use_early=False)
        current = manager._desired_for(room, schedules, settings, minute, use_early=False)
        if (
            target is None
            or current is None
            or current_mode not in (None, mode)
            or future_mode not in (None, mode)
        ):
            self.candidates.pop(key, None)
            return None
        sign = 1 if mode == "heat" else -1
        target_c = manager._stored_setpoint_c(target, settings)
        identity = (now.date().isoformat(), start, block.get("temp"), mode, target_c)
        if sign * (target - current) <= 0:
            self.candidates.pop(key, None)
            return None
        if identity == old and sum(s["mode"] == mode for s in samples) >= 3:
            return old
        eta = estimate(samples, mode, indoor, outdoor, target_c)
        status["estimate_minutes"] = eta
        if eta is None or sign * (target_c - indoor) < 0.3 or start - minute > eta:
            self.candidates.pop(key, None)
            return None
        candidate, since = self.candidates.get(key, (None, 0))
        if candidate != identity:
            self.candidates[key] = identity, now.timestamp()
        elif now.timestamp() - since >= 60:
            return identity
        return None

    async def update(self):
        iid = self.hass.data[DOMAIN].get("active_instance_id") or "default"
        manager = self.managers.get(iid)
        if self.active_manager is not manager:
            if self.active_manager is not None:
                self.active_manager._early_blocks = {}
                self.runs.clear()
            self.candidates.clear()
            self.active_manager = manager
        if manager is None:
            return
        schedules, settings = manager._get_data()
        configured = settings.get("thermal_rooms")
        rules = (
            {room: rule for room, rule in configured.items() if isinstance(rule, dict)}
            if isinstance(configured, dict)
            else {}
        )
        now = dt_util.now()
        stamp, minute = now.timestamp(), manager._now_min()
        active = manager._auto_apply_enabled()
        old = getattr(manager, "_early_blocks", {})
        early, status, live = {}, {}, set()
        valves = Counter(r.get("valve") for room, r in rules.items() if room in schedules and r.get("floor"))
        for room, rule in rules.items():
            if room not in schedules or not (rule.get("learn") or rule.get("floor")):
                continue
            key = iid + "/" + room
            live.add(key)
            state = self.hass.states.get(room)
            indoor = self.reading(
                rule.get("sensor") or (settings.get("temp_sensors") or {}).get(room) or room
            )
            hold = (settings.get("room_pause") or {}).get(room) or {}
            owd = manager._owd_mgr()
            control = (
                active
                and (settings.get("apply_enabled") or {}).get(room, True)
                and not manager._room_control_paused(settings, room)
                and not hold.get("indef")
                and (hold.get("until_ms") or 0) <= stamp * 1000
            )
            allowed = (
                control
                and not manager._summer_off(room, settings)
                and not (owd and owd.is_entity_suspended(room))
            )
            mode = state.state if state else None
            keep = retention_days(rule)
            if rule.get("learn") and self.retention.get(key) != keep:
                self.retention[key] = keep
                self.save_needed = True
            samples = self.history.setdefault(key, []) if rule.get("learn") else []
            first = len(samples)
            samples[:] = [s for s in samples if s["at"] > stamp - keep * 86400]
            if len(samples) != first:
                self.save_needed = True
            outdoor = self.reading(rule.get("outdoor"))
            report = status[room] = dict(outdoor_c=outdoor, samples=len(samples), early=False)
            if outdoor is not None:
                previous = self.previous_outdoor.setdefault(key, (stamp, outdoor))
                report["trend"] = (
                    "↑" if outdoor > previous[1] + 0.1 else "↓" if outdoor < previous[1] - 0.1 else "→"
                )
                if stamp - previous[0] >= 1800:
                    self.previous_outdoor[key] = stamp, outdoor
            if (
                rule.get("learn")
                and allowed
                and mode in ("heat", "cool")
                and indoor is not None
                and outdoor is not None
            ):
                target = celsius(state.attributes.get("temperature"), self.hass.config.units.temperature_unit)
                if target is not None:
                    self.observe(
                        key,
                        samples,
                        stamp,
                        mode,
                        indoor,
                        outdoor,
                        target,
                        state.attributes.get("hvac_action"),
                    )
                hit = self.early_block(
                    key,
                    manager,
                    room,
                    schedules,
                    settings,
                    minute,
                    now,
                    indoor,
                    outdoor,
                    mode,
                    samples,
                    old.get(room),
                    report,
                )
                if hit:
                    early[room] = hit
                    report["early"] = True
            else:
                self.candidates.pop(key, None)
                self.runs.pop(key, None)
            if control and rule.get("floor") and valves[rule.get("valve")] == 1:
                await self.apply_valve(room, rule, state, indoor, allowed)
        for cache in (self.runs, self.candidates, self.previous_outdoor):
            for key in cache.keys() - live:
                del cache[key]
        # Disabling learning pauses collection; existing samples still age out.
        instances = self.hass.data[DOMAIN].get("instances") or {}
        for key in list(self.history):
            owner, _, room = key.partition("/")
            stored_rules = ((instances.get(owner) or {}).get("settings") or {}).get("thermal_rooms") or {}
            r = stored_rules.get(room) or {}
            days = retention_days(r) if r else self.retention.get(key, 7)
            rows = self.history[key]
            cutoff = stamp - days * 86400
            if rows and rows[0]["at"] <= cutoff:
                rows[:] = [sample for sample in rows if sample["at"] > cutoff]
                self.save_needed = True
            if not r and not rows:
                del self.history[key]
                self.retention.pop(key, None)
                self.save_needed = True
        self.status = {iid: status}
        manager._early_blocks = early
        for room in old.keys() | early.keys():
            if old.get(room) != early.get(room) and room in schedules:
                targets = {room, *(settings.get("merges") or {}).get(room, [])}
                await manager._maybe_apply_now(only_targets=targets)
                await manager._maybe_control_boiler()

    async def apply_valve(self, room, rule, state, indoor, allowed):
        valve = rule.get("valve") or ""
        device = self.hass.states.get(valve) if valve.startswith("number.") else None
        if not device or device.attributes.get("unit_of_measurement") != "%" or numeric(device.state) is None:
            return
        attrs = device.attributes
        if numeric(attrs.get("min")) != 0 or numeric(attrs.get("max")) != 100:
            return
        # Use the actual climate setpoint, including manual changes. For a
        # helper-backed room the helper itself carries the applied setpoint.
        helper = room.startswith("input_number.")
        target = (
            celsius(
                state.state if helper else state.attributes.get("temperature"),
                (state.attributes.get("unit_of_measurement") or self.hass.config.units.temperature_unit)
                if helper
                else self.hass.config.units.temperature_unit,
            )
            if state
            else None
        )
        heating = bool(
            state and state.state not in ("unknown", "unavailable") and (helper or state.state == "heat")
        )
        opening = 0
        if allowed and heating and indoor is not None and target is not None:
            opening = valve_position(
                target - indoor,
                rule.get("regulation"),
                numeric(device.state),
                max(0.01, numeric(attrs.get("step")) or 1),
            )
        if abs(float(device.state) - opening) > 0.001:
            try:
                await self.hass.services.async_call(
                    "number", "set_value", {"entity_id": valve, "value": opening}, blocking=True
                )
            except Exception:
                _LOGGER.exception("Could not set floor valve %s", valve)
