"""Exercise the installed Timeline manager without a running HA dependency."""
import ast
import asyncio
import copy
import logging
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace


class ManualTargetTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 9, 10, 0, tzinfo=timezone.utc)
        source = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/__init__.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        manager = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AutoApplyManager")
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), manager], type_ignores=[])
        self.globals = {
            "asyncio": asyncio, "timedelta": timedelta, "DOMAIN": "thermostat_timeline",
            "_norm_instance_id": lambda value: value or "default", "callback": lambda fn: fn,
            "_LOGGER": logging.getLogger("test"), "_f_to_c": lambda f: (f - 32) * 5 / 9,
            "_c_to_f": lambda c: c * 9 / 5 + 32, "UnitOfTemperature": SimpleNamespace(FAHRENHEIT="°F"),
            "time": SimpleNamespace(time=lambda: self.now.timestamp()),
            "dt_util": SimpleNamespace(now=lambda: self.now, utcnow=lambda: self.now,
                                       as_utc=lambda dt: dt, utc_from_timestamp=lambda ts: datetime.fromtimestamp(ts, timezone.utc)),
        }
        exec(compile(ast.fix_missing_locations(module), "installed_timeline_manager", "exec"), self.globals)
        self.Manager = self.globals["AutoApplyManager"]
        self.a, self.b = "climate.study", "climate.bedroom"
        self.schedules = {eid: {"defaultTemp": 15, "blocks": [
            {"startMin": 405, "endMin": 480, "temp": 19},
            {"startMin": 1020, "endMin": 1260, "temp": 19},
        ]} for eid in (self.a, self.b)}
        self.settings = {"auto_apply_enabled": True, "storage_temp_unit": "C", "room_pause": {}}
        self.states = {eid: SimpleNamespace(state="heat", attributes={"temperature": 15, "hvac_modes": ["heat", "off"]}) for eid in self.schedules}
        self.calls, self.saved = [], None

        async def call(domain, service, data, blocking=False):
            self.calls.append((domain, service, copy.deepcopy(data)))
            if domain == "thermostat_timeline":
                self.assertFalse(data["activate"])
                self.settings.update(copy.deepcopy(data["settings"]))
                self.saved = copy.deepcopy(self.settings)
            elif domain == "climate" and service == "set_temperature":
                self.states[data["entity_id"]].attributes["temperature"] = data["temperature"]

        self.hass = SimpleNamespace(states=SimpleNamespace(get=self.states.get),
                                    services=SimpleNamespace(async_call=call),
                                    config=SimpleNamespace(units=SimpleNamespace(temperature_unit="°C")))
        self.mgr = self.make_manager()

    def make_manager(self):
        mgr = self.Manager(self.hass)
        mgr._get_data = lambda: (self.schedules, self.settings)
        mgr._effective_blocks_today = lambda row, settings, primary=None: row["blocks"]
        mgr._desired_for = lambda eid, schedules, settings, minute: 15
        mgr._owd_mgr = lambda: None
        return mgr

    def test_room_targets_follow_schedule_and_away_ceiling(self):
        del self.mgr._desired_for  # Exercise the real manager instead of the manual-hold stub.
        sensor = "binary_sensor.study"
        person = "person.resident"
        self.states[sensor] = SimpleNamespace(state="on")
        self.states[person] = SimpleNamespace(state="home")
        self.settings.update(presence_sensor_enabled=True, presence_sensors={self.a: sensor},
                             presence_sensor_temps={self.a: 22},
                             away={"enabled": True, "persons": [person], "target_c": 17})

        def target(room):
            return self.mgr._desired_for(room, self.schedules, self.settings, 420)

        self.assertEqual(target(self.a), 22)
        self.settings["presence_offsets_c"] = {self.a: 2}
        self.assertEqual(target(self.a), 21)
        self.states[sensor].state = "off"
        self.assertEqual(target(self.a), 19)
        self.states[person].state = "not_home"
        self.states[sensor].state = "on"
        self.settings["away_room_targets_c"] = {self.a: 16}
        self.assertEqual(target(self.a), 16)
        self.assertEqual(target(self.b), 17)
        self.settings["away_room_targets_c"].clear()
        self.assertEqual(target(self.a), 17)

    async def test_mode_only_boundary_and_temperature_only_with_turn_on_enabled(self):
        del self.mgr._desired_for
        self.mgr._now_min = lambda: 420
        self.settings.update(block_mode_rooms={self.a: True}, turn_on={self.a: {"enabled": True}})
        block = self.schedules[self.a]["blocks"][0]
        block["hvac_mode"] = "off"
        state = self.states[self.a]
        state.attributes.update(temperature=19, preset_modes=["manual"], preset_mode="boost")
        await self.mgr._maybe_apply_now(only_targets={self.a})
        self.assertEqual(self.calls, [("climate", "set_hvac_mode", {"entity_id": self.a, "hvac_mode": "off"})])
        self.calls.clear()
        state.state = "off"
        block["hvac_mode"] = "temperature_only"
        block["temp"] = 22
        await self.mgr._maybe_apply_now(only_targets={self.a})
        self.assertEqual(self.calls, [("climate", "set_temperature", {"entity_id": self.a, "temperature": 22})])
        self.calls.clear()
        block["hvac_mode"] = "heat"
        await self.mgr._maybe_apply_now(only_targets={self.a})
        self.assertEqual([c[1] for c in self.calls], ["set_hvac_mode", "set_temperature"])
        self.calls.clear()
        self.settings["room_pause"] = {self.a: {"indef": True}}
        block["hvac_mode"] = "off"
        await self.mgr._maybe_apply_now(only_targets={self.a})
        self.assertEqual(self.calls, [])
        self.settings["room_pause"] = {}
        self.settings["merges"] = {self.a: ["climate.extra"]}
        self.assertEqual(self.mgr._block_mode("climate.extra", self.schedules, self.settings, 420), "off")
        self.assertIsNone(self.mgr._block_mode(self.a, self.schedules, self.settings, 600))
        self.settings["block_mode_rooms"] = {}
        self.assertIsNone(self.mgr._block_mode(self.a, self.schedules, self.settings, 420))

    async def test_effective_pause_notifications_and_independent_holds(self):
        guest = "input_boolean.guests"
        rule = {"paused": True, "resumed": True}
        self.settings.update(room_pause_controls={self.a: guest, self.b: guest},
                             pause_notifications=rule)
        self.states[guest] = SimpleNamespace(state="off")
        self.mgr._is_active_instance = lambda: True
        tasks = []
        self.hass.async_create_task = lambda coro: tasks.append(asyncio.create_task(coro))

        async def messages():
            released = self.mgr._refresh_pause_state()
            await asyncio.gather(*tasks)
            tasks.clear()
            sent = [data["message"] for _, _, data in self.calls]
            self.calls.clear()
            return released, sent

        self.assertEqual(await messages(), (set(), []))
        self.states[guest].state = "on"
        self.assertEqual(len((await messages())[1]), 2)
        self.settings["room_pause"] = {self.a: {"indef": True}}
        self.assertEqual((await messages())[1], [])
        self.states[guest].state = "off"
        released, sent = await messages()
        self.assertEqual(released, {self.a, self.b})
        self.assertEqual(sent, [f"{self.b} resumed."])
        self.settings["pause_indef"] = True
        self.assertEqual(len((await messages())[1]), 1)
        self.settings["pause_indef"] = False
        self.assertEqual((await messages())[1], ["Global schedule resumed."])
        rule["resumed"] = False
        self.settings["room_pause"] = {}
        self.assertEqual((await messages())[1], [])
        del self.states[guest]
        self.assertTrue(self.mgr._room_control_paused(self.settings, self.a))
        await self.mgr._send_pause_notification({"destination": "entity:notify.office"}, "test")
        self.assertEqual(self.calls[-1][:2], ("notify", "send_message"))
        self.assertEqual(self.calls[-1][2]["entity_id"], "notify.office")

    def test_person_link_replaces_household_rules_only_for_assigned_rooms(self):
        del self.mgr._desired_for
        del self.mgr._effective_blocks_today
        self.mgr._active_presence_combo_key = lambda settings: "family"
        self.settings.update(away={"advanced_enabled": True, "target_c": 17},
                             room_persons={self.a: "person.anna"},
                             away_room_targets_c={self.a: 16}, merges={self.a: ["climate.linked"]},
                             presence_sensor_enabled=True, presence_sensors={self.a: "binary_sensor.study"},
                             presence_sensor_temps={self.a: 23})
        anna = self.states["person.anna"] = SimpleNamespace(state="home")
        sensor = self.states["binary_sensor.study"] = SimpleNamespace(state="off")
        for row in self.schedules.values():
            row["presence"] = {"family": {"blocks": [{"startMin": 0, "endMin": 1440, "temp": 24}]}}

        def target(room, minute=420):
            return self.mgr._desired_for(room, self.schedules, self.settings, minute)

        self.assertEqual(target(self.a), 19)
        self.assertEqual(target(self.b), 24)
        self.settings["room_persons"][self.b] = "person.anna"
        for state in ("work", "not_home"):
            anna.state = state
            sensor.state = "on"
            self.assertEqual(target(self.a), 16)
            self.assertEqual(target("climate.linked"), 16)
            self.assertEqual(target(self.b), 17)
        anna.state = "home"
        self.assertEqual(target(self.a), 23)
        sensor.state = "off"
        for state in ("home", "unknown", "unavailable"):
            anna.state = state
            self.assertEqual(target(self.a, 600), 15)
        del self.states["person.anna"]
        self.assertEqual(target(self.a), 19)
        del self.settings["room_persons"][self.a]
        self.assertEqual(target(self.a), 24)

    def test_vacancy_economy_follows_mode_schedule_and_sensor_delays(self):
        del self.mgr._desired_for
        sensor = "binary_sensor.study"
        st = self.states[sensor] = SimpleNamespace(state="off", last_changed=self.now)
        self.settings.update(presence_sensor_enabled=True, presence_sensors={self.a: sensor},
                             presence_sensor_delays={self.a: {"off_s": 60, "on_s": 30}},
                             vacancy_offsets_c={self.a: 2}, min_temp=14, max_temp=20)

        def target(minute=420):
            return self.mgr._desired_for(self.a, self.schedules, self.settings, minute)

        self.assertEqual(target(), 19)
        self.now += timedelta(seconds=60)
        self.assertEqual(target(), 17)
        self.assertEqual(target(600), 14)
        self.states[self.a].state = "cool"
        self.assertEqual(target(), 20)
        self.states[self.a].state = "heat_cool"
        self.assertEqual(target(), 19)
        self.states[self.a].state = "heat"
        st.state, st.last_changed = "on", self.now
        self.assertEqual(target(), 17)
        self.now += timedelta(seconds=30)
        self.assertEqual(target(), 19)
        st.state = "unavailable"
        self.assertEqual(target(), 19)
        st.state, st.last_changed = "off", self.now
        self.assertEqual(target(), 19)
        self.now += timedelta(seconds=60)
        self.settings.update(away={"enabled": True, "persons": ["person.test"], "target_c": 16})
        self.assertEqual(target(), 16)
        self.settings.update(away={}, vacancy_offsets_c={})
        self.assertEqual(target(), 19)

    def test_boiler_uses_only_live_manual_holds_in_celsius(self):
        settings = dict(self.settings, storage_temp_unit="F", merges={self.a: [self.b]})
        self.mgr._desired_for = lambda *args: 68
        hold = {"source": "manual_target", "target_c": 23,
                "until_ms": (self.now.timestamp() + 60) * 1000}
        settings["room_pause"] = {self.a: hold}
        def target():
            return self.mgr._boiler_target_c(self.b, self.schedules, settings, 600)
        self.assertEqual(target(), 20)
        settings["boiler_manual_targets"] = True
        self.assertEqual(target(), 23)
        hold["source"] = "automation"
        self.assertEqual(target(), 20)
        hold["source"] = "manual_target"
        self.now += timedelta(minutes=1)
        self.assertEqual(target(), 20)

    def test_workday_sensor_fallback_and_holiday_priority(self):
        rule = {"today": "binary_sensor.today", "tomorrow": "binary_sensor.tomorrow",
                "enabled": True, "on_off": "thu"}
        settings = dict(self.settings, weekdays_enabled=True, workday_plans=rule)
        today = self.states[rule["today"]] = SimpleNamespace(state="on")
        tomorrow = self.states[rule["tomorrow"]] = SimpleNamespace(state="on")
        del self.mgr._effective_blocks_today
        self.mgr._today_key = lambda: "wed"
        days = {day: [{"temp": temp}] for day, temp in
                zip(("mon", "thu", "sat", "sun", "wed"), (19, 22, 18, 17, 20))}
        row = {"weekly": {"days": days}, "holiday": {"blocks": [{"temp": 24}]}}
        def target():
            return self.mgr._effective_blocks_today(row, settings)[0]["temp"]
        for a, b, expected in (("on","on",19), ("on","off",22), ("off","off",18),
                               ("off","on",17), ("unknown","on",20)):
            today.state, tomorrow.state = a, b
            self.assertEqual(target(), expected)
        today.state = "on"
        rule["enabled"] = False
        self.assertEqual(target(), 20)
        rule["enabled"] = True
        self.mgr._is_holiday_active = lambda config: True
        self.assertEqual(target(), 24)

    def test_manual_trip_edges_are_exclusive_and_union_with_dates(self):
        self.globals["dt_util"].parse_datetime = datetime.fromisoformat
        self.settings.update(holidays_enabled=True, holidays_source="manual", holidays_dates=[],
                             holiday_trips=[{"start": "2026-11-09T10:15", "end": "2026-11-09T10:45"},
                                            {"start": "2026-11-09T10:30", "end": "2026-11-09T11:00"}])
        for hour, minute, active in [(10,14,False),(10,15,True),(10,45,True),(11,0,False)]:
            self.now = self.now.replace(hour=hour, minute=minute)
            self.assertEqual(self.mgr._is_holiday_active(self.settings), active)
        self.settings["holidays_dates"] = ["2026-11-09"]
        self.assertTrue(self.mgr._is_holiday_active(self.settings))
        self.settings["holidays_enabled"] = False
        self.assertFalse(self.mgr._is_holiday_active(self.settings))

    def test_trip_departure_ends_a_manual_hold_only_in_rooms_with_holiday_blocks(self):
        self.globals["dt_util"].parse_datetime = datetime.fromisoformat
        self.settings.update(holidays_enabled=True, holidays_source="manual",
                             holiday_trips=[{"start": "2026-11-09T10:15", "end": "2026-11-10T12:00"}])
        row = dict(self.schedules[self.a], holiday={"blocks": [{"temp": 17}]})
        expected = self.now.replace(minute=15).timestamp() * 1000
        self.assertEqual(self.mgr._manual_target_expiry(row, self.settings), expected)
        self.assertGreater(self.mgr._manual_target_expiry(self.schedules[self.b], self.settings), expected)

    async def test_summer_off_only_restores_modes_owned_by_timeline(self):
        self.settings.update(seasonal_enabled=True, seasonal_mode="summer", summer_off_rooms=[self.a])
        self.assertTrue(await self.mgr._sync_summer_power(self.a))
        self.assertEqual(self.settings["summer_previous_modes"], {self.a: "heat"})
        self.assertEqual(self.calls[-1][2]["hvac_mode"], "off")
        self.states[self.a].state = "off"
        self.calls.clear()
        self.assertTrue(await self.mgr._sync_summer_power(self.a))
        self.assertFalse(await self.mgr._sync_summer_power(self.b))
        self.assertEqual(self.calls, [])
        self.settings["seasonal_mode"] = "winter"
        self.assertFalse(await self.make_manager()._sync_summer_power(self.a))
        self.assertEqual(self.calls[0][2]["hvac_mode"], "heat")
        self.assertEqual(self.settings["summer_previous_modes"], {})
        self.settings["seasonal_mode"] = "summer"
        self.calls.clear()
        self.assertTrue(await self.mgr._sync_summer_power(self.a))
        self.assertEqual(self.calls, [])

    async def manual(self, eid, value):
        self.states[eid].attributes["temperature"] = value
        await self.mgr._remember_manual_target(eid, value)

    async def test_automatic_holds_can_be_disabled_without_affecting_explicit_pauses(self):
        self.settings["manual_target_hold"] = {"enabled": False, "minutes": 30}
        explicit_pause = {"indef": True}
        self.settings["room_pause"][self.b] = explicit_pause

        await self.manual(self.a, 20)
        await self.manual(self.b, 21)

        self.assertEqual(self.settings["room_pause"], {self.b: explicit_pause})
        self.assertEqual(self.calls, [])

    async def test_fixed_hold_crosses_midnight_and_reconciles_at_expiry(self):
        self.now = self.now.replace(hour=23, minute=55)
        self.settings["manual_target_hold"] = {"minutes": 30}
        expires_at = self.now + timedelta(minutes=30)

        await self.manual(self.a, 20)
        self.assertEqual(self.mgr._next_room_pause_dt(), (expires_at, self.a))
        self.now += timedelta(minutes=5)
        await self.mgr._maybe_apply_now(force=True, reconcile=True)
        self.assertEqual(self.states[self.a].attributes["temperature"], 20)

        self.now = expires_at
        self.mgr._next_room_resume = self.a
        self.mgr._next_room_resume_at = expires_at
        self.globals["async_track_point_in_utc_time"] = lambda *args: None
        await self.mgr._timer_fire()
        self.assertEqual(self.states[self.a].attributes["temperature"], 15)

    async def test_manual_hold_survives_both_startup_apply_paths(self):
        await self.manual(self.a, 20)
        hold = self.settings["room_pause"][self.a]
        self.assertEqual(hold["until_ms"], self.now.replace(hour=17).timestamp() * 1000)
        self.assertEqual(hold["target_c"], 20)
        self.settings = copy.deepcopy(self.saved)  # Load the persisted settings after restart.
        restored = self.make_manager()
        self.calls.clear()
        await restored._maybe_apply_now(force=True)
        await restored._maybe_apply_now(force=True, reconcile=True)
        await restored.async_apply_entity_now(self.a, reconcile=True)  # Late entity recovery.
        self.assertEqual(self.states[self.a].attributes["temperature"], 20)
        self.assertFalse(any(domain == "climate" for domain, _, _ in self.calls))

    async def test_native_room_resume_releases_only_expired_room(self):
        await self.manual(self.a, 20)
        self.now = self.now.replace(hour=17)
        self.mgr._next_room_resume = self.a
        self.mgr._next_room_resume_at = self.now
        async def noop(*args, **kwargs):
            pass
        self.mgr._maybe_control_boiler = noop
        self.mgr._schedule_next = noop
        self.calls.clear()
        await self.mgr._timer_fire()
        climate_calls = [(s, d) for domain, s, d in self.calls if domain == "climate"]
        self.assertEqual(climate_calls, [("set_temperature", {"entity_id": self.a, "temperature": 15.0})])
        self.assertEqual(self.states[self.b].attributes["temperature"], 15)

    async def test_restart_after_missed_boundary_applies_schedule(self):
        await self.manual(self.a, 20)
        self.now = self.now.replace(hour=18)
        restored = self.make_manager()
        await restored._maybe_apply_now(force=True, reconcile=True)
        self.assertEqual(self.states[self.a].attributes["temperature"], 15)

    async def test_schedule_writes_do_not_create_holds_and_cancel_owned_hold(self):
        await self.manual(self.a, 15)
        self.assertEqual(self.settings["room_pause"], {})
        await self.manual(self.a, 20)
        await self.manual(self.a, 15)
        self.assertEqual(self.settings["room_pause"], {})

    async def test_clamped_schedule_write_does_not_create_manual_hold(self):
        attrs = self.states[self.a].attributes
        attrs.update(temperature=18, min_temp=16)
        self.assertTrue(await self.mgr._apply_setpoint(self.a, 15))
        self.assertEqual(attrs["temperature"], 16)
        await self.mgr._remember_manual_target(self.a, attrs["temperature"])
        self.assertEqual(self.settings["room_pause"], {})
        self.assertTrue(await self.mgr._apply_setpoint(self.a, 20))

    async def test_fahrenheit_schedule_write_does_not_create_manual_hold(self):
        self.settings["storage_temp_unit"] = "F"
        self.hass.config.units.temperature_unit = "?F"
        self.states[self.a].attributes.update(temperature=70, max_temp=75)
        self.mgr._desired_for = lambda *args: 77
        self.assertTrue(await self.mgr._apply_setpoint(self.a, 77))
        reported = self.states[self.a].attributes["temperature"]
        self.assertAlmostEqual(reported, 75)
        await self.mgr._remember_manual_target(self.a, reported)
        self.assertEqual(self.settings["room_pause"], {})

    async def test_independent_manual_changes_preserve_both_rooms(self):
        self.states[self.a].attributes["temperature"] = 20
        self.states[self.b].attributes["temperature"] = 21
        await asyncio.gather(self.mgr._remember_manual_target(self.a, 20), self.mgr._remember_manual_target(self.b, 21))
        self.assertEqual(set(self.saved["room_pause"]), {self.a, self.b})

    async def test_existing_user_pause_and_disabled_room_are_preserved(self):
        self.settings["room_pause"][self.a] = {"indef": True}
        await self.manual(self.a, 20)
        self.assertEqual(self.settings["room_pause"][self.a], {"indef": True})
        self.settings["apply_enabled"] = {self.b: False}
        await self.manual(self.b, 20)
        self.assertNotIn(self.b, self.settings["room_pause"])

    async def test_superseded_events_do_not_store_stale_targets(self):
        self.states[self.a].attributes["temperature"] = 21
        await self.mgr._remember_manual_target(self.a, 20)
        self.assertEqual(self.settings["room_pause"], {})

    async def test_target_watcher_captures_ha_and_dial_handoff_changes(self):
        listeners, tasks = [], []
        def track(hass, entities, listener):
            listeners.append(listener)
            return lambda: None
        self.globals["async_track_state_change_event"] = track
        self.hass.async_create_task = lambda coro: tasks.append(asyncio.create_task(coro))
        self.mgr._reset_target_recovery_watch()
        self.mgr._reset_target_recovery_watch()  # A pause/settings save keeps the listener attached.
        self.assertEqual(len(listeners), 1)
        old = SimpleNamespace(attributes={"temperature": 15})
        self.states[self.a].attributes["temperature"] = 20
        listeners[0](SimpleNamespace(data={"entity_id": self.a, "old_state": old, "new_state": self.states[self.a]}))
        await asyncio.gather(*tasks)
        self.assertEqual(self.saved["room_pause"][self.a]["target_c"], 20)

    async def test_midnight_boundary_and_fahrenheit(self):
        self.now = self.now.replace(hour=23)
        await self.manual(self.a, 20)
        tomorrow = (self.now + timedelta(days=1)).replace(hour=0)
        self.assertEqual(self.settings["room_pause"][self.a]["until_ms"], tomorrow.timestamp() * 1000)
        self.hass.config.units.temperature_unit = "°F"
        await self.manual(self.a, 68)
        self.assertEqual(self.settings["room_pause"][self.a]["target_c"], 20)


if __name__ == "__main__":
    unittest.main()
