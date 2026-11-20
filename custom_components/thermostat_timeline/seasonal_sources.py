"""Apply the active Timeline instance's seasonal plant selection in Home Assistant."""
from __future__ import annotations

import logging
import math
from datetime import timedelta
from time import monotonic, time

from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_call_later, async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store

from .const import DOMAIN, SIGNAL_UPDATED

_LOGGER = logging.getLogger(__name__)


class SeasonalSources:
    def __init__(self, hass, entry, managers):
        self.hass = hass
        self.entry = entry
        self.managers = managers
        self.store = Store(hass, 1, DOMAIN + ".seasonal_source")
        self.owner = {}
        self.applied = None
        self.entities = ()
        self.unsubscribe = None
        self.task = None
        self.dirty = False
        self.retries = {}
        self.stop_report = {}
        self.cancel_deadline = None

    async def start(self):
        self.owner = await self.store.async_load() or {}
        self.entry.async_on_unload(async_dispatcher_connect(self.hass, SIGNAL_UPDATED, self.wake))
        self.entry.async_on_unload(async_track_time_interval(self.hass, self.wake, timedelta(seconds=30)))
        self.entry.async_on_unload(self.close)
        self.wake()

    def clear_deadline(self):
        if self.cancel_deadline:
            self.cancel_deadline()
            self.cancel_deadline = None

    def close(self):
        self.clear_deadline()
        if self.unsubscribe:
            self.unsubscribe()
        if self.task:
            self.task.cancel()

    @callback
    def wake(self, *_):
        self.dirty = True
        if self.task is None or self.task.done():
            self.task = self.entry.async_create_background_task(
                self.hass, self.run(), "Timeline seasonal source", eager_start=False)

    async def run(self):
        while self.dirty:
            self.dirty = False
            try:
                await self.reconcile()
            except Exception:
                _LOGGER.exception("Seasonal source change did not complete")

    def watch(self, entities):
        entities = tuple(sorted(set(filter(None, entities))))
        if entities == self.entities:
            return
        if self.unsubscribe:
            self.unsubscribe()
        self.entities = entities
        self.unsubscribe = async_track_state_change_event(self.hass, entities, self.wake) if entities else None

    def plan(self):
        instance = self.hass.data[DOMAIN].get("active_instance_id") or "default"
        manager = self.managers.get(instance)
        if not manager:
            return None
        schedules, settings = manager._get_data()
        rule = settings.get("seasonal_sources") or {}
        if not (settings.get("seasonal_enabled") and rule.get("enabled") and manager._auto_apply_enabled()):
            return None
        season = manager._season_key(settings)
        follow = settings.get("season_follow") or {}
        if follow.get("enabled") and not manager._observed_season(settings) and not settings.get("sensor_season_last"):
            return None
        active = rule.get(season) or {}
        entity = active.get("entity") or ""
        peer = (rule.get("winter" if season == "summer" else "summer") or {}).get("entity") or ""
        mode = active.get("mode")
        if not all(e.startswith("climate.") for e in (entity, peer)) or mode not in ("heat", "cool", "off"):
            return None
        room_targets = manager._all_targets(schedules, settings.get("merges") or {}) | set(settings.get("entities") or [])
        if room_targets.intersection((entity, peer)):
            return None
        delay = rule.get("off_delay_minutes", 3) if rule.get("off_delay_enabled") else 0
        if rule.get("off_delay_enabled") and (type(delay) is not int or delay < 1):
            return None
        return instance, season, entity, peer, mode, active.get("target_c"), delay

    async def remember(self, entity, starting, mode=None, confirmed_at=None):
        record = {"entity": entity, "starting": starting}
        if confirmed_at is not None:
            record["confirmed_at"] = confirmed_at
        if starting:
            record["mode"] = mode
        if self.owner != record:
            await self.store.async_save(record)
            self.owner = record
            self.stop_report.pop(entity, None)

    def state(self, entity):
        return self.hass.states.get(entity)

    async def command(self, entity, service, **fields):
        key = (entity, service)
        signature = tuple(fields.items())
        previous, when = self.retries.get(key, (None, 0))
        if previous == signature and monotonic() - when < 15:
            return
        self.retries[key] = signature, monotonic()
        await self.hass.services.async_call("climate", service, {"entity_id": entity, **fields}, blocking=True)

    async def confirmed_off(self, entity):
        state = self.state(entity)
        if not state or state.state in ("unavailable", "unknown"):
            return False
        uncertain = self.owner.get("starting") and self.owner.get("entity") == entity
        if state.state != "off" or (uncertain and
                self.stop_report.get(entity, state.last_reported) == state.last_reported):
            if "off" not in (state.attributes.get("hvac_modes") or []):
                return False
            self.stop_report.setdefault(entity, state.last_reported)
            await self.command(entity, "set_hvac_mode", hvac_mode="off")
            state = self.state(entity)
            if not state or state.state != "off" or (uncertain and
                    self.stop_report[entity] == state.last_reported):
                return False
        if uncertain:
            # The entity may have displayed Off throughout an unacknowledged start.
            await self.remember(entity, False, confirmed_at=state.last_reported.timestamp())
        self.stop_report.pop(entity, None)
        return True

    def delay_elapsed(self, entities, minutes):
        if not minutes:
            return True
        since = 0
        for entity in entities:
            state = self.state(entity)
            if not state or state.state != "off":
                return False
            since = max(since, state.last_changed.timestamp())
            if self.owner.get("entity") == entity:
                since = max(since, self.owner.get("confirmed_at", 0))
        remaining = since + minutes * 60 - time()
        if remaining <= 0:
            return True
        # Long waits already have the regular 30-second reconciliation tick.
        if remaining <= 30:
            self.cancel_deadline = async_call_later(self.hass, remaining, self.wake)
        return False

    async def reconcile(self):
        self.clear_deadline()
        plan = self.plan()
        if not plan:
            self.watch(())
            self.applied = None
            return
        if self.applied != plan:
            self.applied = None
        _, _, entity, peer, mode, target_c, delay = plan
        previous = self.owner.get("entity")
        self.watch([entity, peer, previous])
        state = self.state(entity)
        if not state or state.state in ("unavailable", "unknown"):
            return
        attrs = state.attributes
        if not {"off", mode}.issubset(attrs.get("hvac_modes") or []):
            return
        target = None
        if target_c is not None and mode != "off":
            if not isinstance(target_c, (int, float)) or not math.isfinite(target_c):
                return
            fahrenheit = "F" in str(self.hass.config.units.temperature_unit)
            target = round(target_c * 1.8 + 32 if fahrenheit else target_c, 2)
            if not (attrs.get("supported_features", 0) & 1 and attrs.get("min_temp", -math.inf) <= target <= attrs.get("max_temp", math.inf)):
                return
        # Remember the previously commanded plant even if an assignment was edited or HA restarted.
        others = set(filter(None, (previous, peer))) - {entity}
        for other in sorted(others):
            if not await self.confirmed_off(other):
                return
        if self.plan() != plan or any(not self.state(e) or self.state(e).state != "off" for e in others):
            return
        if self.applied == plan:
            return
        if mode == "off":
            if await self.confirmed_off(entity):
                await self.remember(entity, False)
                self.applied = plan
            return
        pending_other_mode = (self.owner.get("starting") and previous == entity and self.owner.get("mode") != mode)
        current = self.state(entity)
        if not current or current.state in ("unknown", "unavailable"):
            return
        if pending_other_mode or current.state not in ("off", mode):
            if not await self.confirmed_off(entity):
                return
        stopped = others | ({entity} if previous == entity or peer == entity else set())
        current = self.state(entity)
        if not current or (current.state == "off" and not self.delay_elapsed(stopped, delay)):
            return
        await self.remember(entity, True, mode)
        if self.plan() != plan or any(not self.state(e) or self.state(e).state != "off" for e in others):
            return
        current = self.state(entity)
        if not current or current.state not in ("off", mode):
            return
        if current.state != mode:
            if not self.delay_elapsed(stopped, delay):
                return
            await self.command(entity, "set_hvac_mode", hvac_mode=mode)
        if self.plan() != plan or not self.state(entity) or self.state(entity).state != mode:
            return
        if any(not self.state(e) or self.state(e).state != "off" for e in others):
            return
        if target is not None and self.state(entity).attributes.get("temperature") != target:
            await self.command(entity, "set_temperature", temperature=target)
            observed = self.state(entity)
            if not observed or observed.attributes.get("temperature") != target:
                return
        await self.remember(entity, False)
        self.applied = plan
        self.retries.clear()
        self.stop_report.clear()
