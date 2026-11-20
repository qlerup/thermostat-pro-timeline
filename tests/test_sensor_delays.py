"""Check that sensor delays stay outside Home Assistant's startup tasks."""
import ast
import asyncio
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


class SensorDelayTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/__init__.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        names = {"PresenceSensorManager", "OpenWindowManager"}
        managers = [node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in names]
        annotations = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
        module = ast.Module(body=[annotations, *managers], type_ignores=[])
        self.namespace = {"asyncio": asyncio, "_norm_instance_id": lambda value: value}
        exec(compile(ast.fix_missing_locations(module), str(source), "exec"), self.namespace)
        self.sensor = SimpleNamespace(state="off")
        self.foreground_tasks = []
        self.background_tasks = []
        self.hass = SimpleNamespace(
            states=SimpleNamespace(get=lambda entity: self.sensor),
            async_create_task=self.create_foreground_task,
        )
        self.entry = SimpleNamespace(async_create_background_task=self.create_background_task)

    def create_foreground_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.foreground_tasks.append(task)
        return task

    def create_background_task(self, hass, coroutine, name, *, eager_start):
        self.assertIs(hass, self.hass)
        self.assertFalse(eager_start)
        task = asyncio.create_task(coroutine, name=name)
        self.background_tasks.append(task)
        return task

    async def asyncTearDown(self):
        tasks = self.foreground_tasks + self.background_tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def test_presence_delays_run_in_background_and_cancel_on_sensor_change(self):
        apply = SimpleNamespace(_maybe_apply_now=AsyncMock(), _schedule_next=AsyncMock())
        manager = self.namespace["PresenceSensorManager"](self.hass, apply, entry=self.entry)
        room = "climate.attic"
        manager._room_sensor[room] = "binary_sensor.attic"
        manager._delays_s[room] = (0, 1800)
        await manager._schedule_room(room, "off")
        delayed = manager._tasks[(room, "off")]
        await asyncio.sleep(0)
        self.assertFalse(delayed.done())
        self.assertIn(delayed, self.background_tasks)
        self.assertEqual(self.foreground_tasks, [])
        apply._maybe_apply_now.assert_not_awaited()
        self.sensor.state = "on"
        await manager._schedule_room(room, "on")
        await asyncio.gather(*self.background_tasks)
        self.assertTrue(delayed.done())
        self.assertEqual(manager._tasks, {})
        apply._maybe_apply_now.assert_awaited_once_with(force=True)
        apply._schedule_next.assert_awaited_once()

    async def test_window_open_and_close_delays_run_in_background(self):
        room = "climate.attic"
        manager = self.namespace["OpenWindowManager"](self.hass, None, entry=self.entry)
        manager._room_sensors[room] = ["binary_sensor.attic"]
        manager._sensor_open = lambda sensor: self.sensor.state == "on"
        manager._settings = dict
        manager._enabled = lambda settings: True
        manager._entities_for_room = lambda room, settings: [room]
        manager._suspend_room = AsyncMock()
        manager._resume_room = AsyncMock()
        manager._open_delay_s = manager._close_delay_s = 1800

        self.sensor.state = "on"
        await manager._evaluate_room(room, {})
        suspend = manager._room_tasks[(room, "suspend")]
        await asyncio.sleep(0)
        self.assertFalse(suspend.done())
        self.assertIn(suspend, self.background_tasks)

        manager._suspended_entities.add(room)
        self.sensor.state = "off"
        await manager._evaluate_room(room, {})
        resume = manager._room_tasks[(room, "resume")]
        await asyncio.sleep(0)
        self.assertTrue(suspend.done())
        self.assertFalse(resume.done())
        self.assertIn(resume, self.background_tasks)
        self.assertEqual(self.foreground_tasks, [])
        manager._suspend_room.assert_not_awaited()
        manager._resume_room.assert_not_awaited()
