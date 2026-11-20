"""Regression tests for learning, rolling retention and percentage room valves."""

import ast
from datetime import datetime, timezone
import math
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


def module():
    path = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/thermal.py"
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    tree.body = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef))]
    ns = dict(
        math=math,
        Store=Mock,
        DOMAIN="timeline",
        Counter=Counter,
        callback=lambda f: f,
        dt_util=SimpleNamespace(now=lambda: datetime.now(timezone.utc)),
    )
    exec(compile(tree, str(path), "exec"), ns)
    return ns


class ThermalTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.module = module()
        self.room = "climate.test"
        self.rule = {"learn": True, "days": 7, "outdoor": "sensor.outdoor"}
        self.settings = {"thermal_rooms": {self.room: self.rule}}
        self.schedules = {self.room: {"blocks": []}}
        self.manager = Mock()
        self.manager._early_blocks = {}
        self.manager._get_data.return_value = self.schedules, self.settings
        self.manager._room_control_paused.return_value = False
        self.manager._summer_off.return_value = False
        self.manager._owd_mgr.return_value = None
        self.manager._now_min.return_value = 600
        self.manager._effective_blocks_today.return_value = []
        self.manager._maybe_apply_now = AsyncMock()
        self.manager._maybe_control_boiler = AsyncMock()
        self.states = {}
        instance = dict(settings=self.settings, schedules=self.schedules)
        hass = SimpleNamespace(
            states=self.states,
            config=SimpleNamespace(units=SimpleNamespace(temperature_unit="°C")),
            data={"timeline": {"instances": {"default": instance}}},
            services=SimpleNamespace(async_call=AsyncMock()),
        )
        self.worker = self.module["ThermalControl"](hass, Mock(), {"default": self.manager})
        self.worker.store = Mock()

    def test_learns_from_completed_independent_heat_and_cool_runs(self):
        samples = []
        for i in range(4):
            direction = 1 if i < 3 else -1
            mode, action = ("heat", "heating") if direction == 1 else ("cool", "cooling")
            for minute in range(21):
                self.worker.observe(
                    "room",
                    samples,
                    10000 + i * 3600 + minute * 60,
                    mode,
                    19 + direction * minute / 20,
                    5,
                    19 + direction,
                    action,
                )
        self.assertEqual(len(samples), 4)
        self.assertAlmostEqual(self.module["estimate"](samples, "heat", 18, 5, 20), 40, delta=1)
        self.assertIsNone(self.module["estimate"](samples, "cool", 20, 5, 18))

    def test_outdoor_conditions_influence_prediction(self):
        samples = [dict(mode="cool", indoor=23, outdoor=t, pace=p) for t, p in [(20, 12), (22, 14), (30, 27)]]
        predict = self.module["estimate"]
        self.assertGreater(predict(samples, "cool", 23, 30, 20), predict(samples, "cool", 23, 20, 20))
        self.assertAlmostEqual(self.module["celsius"](68, "°F"), 20)
        self.assertIsNone(self.module["celsius"]("unavailable", "°C"))

    async def test_rolling_window_with_changed_retention(self):
        now = datetime.now(timezone.utc).timestamp()
        key = "default/" + self.room
        self.worker.history[key] = [dict(at=now - days * 86400) for days in [9, 6, 2]]
        await self.worker.update()
        self.assertEqual(len(self.worker.history[key]), 2)
        self.rule["days"] = 3
        await self.worker.update()
        self.assertEqual(len(self.worker.history[key]), 1)

    def test_interrupted_or_stalled_runs_do_not_train(self):
        samples = []
        self.worker.observe("room", samples, 0, "cool", 24, 30, 20, "cooling")
        self.worker.observe("room", samples, 300, "cool", 20, 30, 20, "idle")
        self.assertEqual(samples, [])
        self.worker.observe("room", samples, 400, "heat", 18, 0, 22, "heating")
        self.worker.observe("room", samples, 460, "heat", 18, 0, 22, "idle")
        self.assertEqual(samples, [])

    async def test_valve_pause_sensor_failure_and_cooling(self):
        self.rule.update(learn=False, floor=True, valve="number.valve", regulation="proportional")
        self.states["number.valve"] = SimpleNamespace(
            state="75", attributes={"unit_of_measurement": "%", "min": 0, "max": 100, "step": 5}
        )
        self.states[self.room] = SimpleNamespace(
            state="heat", attributes={"current_temperature": 20, "temperature": 21}
        )
        service = self.worker.hass.services.async_call
        await self.worker.update()
        self.assertEqual(service.await_args.args[2]["value"], 50)
        self.rule["sensor"] = "sensor.missing"
        await self.worker.update()
        self.assertEqual(service.await_args.args[2]["value"], 0)
        self.rule.pop("sensor")
        self.states[self.room].state = "cool"
        await self.worker.update()
        self.assertEqual(service.await_args.args[2]["value"], 0)
        self.settings["pause_indef"] = True
        self.manager._auto_apply_enabled.return_value = False
        service.reset_mock()
        await self.worker.update()
        service.assert_not_awaited()

    def test_valve_hysteresis_and_step(self):
        position = self.module["valve_position"]
        self.assertEqual(position(0.15, "binary", 100, 1), 100)
        self.assertEqual(position(0.15, "binary", 0, 1), 0)
        self.assertEqual(position(0.41, "binary", 0, 1), 100)
        self.assertEqual(position(-0.1, "binary", 100, 1), 0)
        self.assertEqual(position(0.61, "proportional", 0, 5), 30)
        self.assertEqual(position(4, "proportional", 0, 5), 100)

    async def test_checkpoints_changed_runs_and_retries_storage_errors(self):
        worker = self.worker
        worker.store.async_save = AsyncMock(side_effect=[OSError("temporary"), None])
        ns = self.module
        ns["_LOGGER"] = Mock()

        def collect():
            worker.runs["default/" + self.room] = dict(start=100, last=130)

        worker.update = AsyncMock(side_effect=collect)
        worker.dirty = True
        await worker.run()
        self.assertTrue(worker.save_needed)
        worker.dirty = True
        await worker.run()
        self.assertFalse(worker.save_needed)
        self.assertEqual(worker.store.async_save.await_count, 2)
        saved = worker.store.async_save.await_args.args[0]
        self.assertEqual(saved["runs"]["default/" + self.room]["last"], 130)
        self.assertEqual(worker.room_data("default", self.room)["in_progress"]["start"], 100)

    async def test_disabled_room_retains_history_until_it_ages_out(self):
        stamp = datetime.now(timezone.utc).timestamp()
        self.rule.update(learn=False, days=2)
        self.worker.history["default/" + self.room] = [{"at": stamp - 86400}, {"at": stamp}]
        await self.worker.update()
        self.assertEqual(len(self.worker.room_data("default", self.room)["completed"]), 2)
        self.worker.history["default/" + self.room][0]["at"] -= 2 * 86400
        await self.worker.update()
        self.assertEqual(len(self.worker.room_data("default", self.room)["completed"]), 1)
