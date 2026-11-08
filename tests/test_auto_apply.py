"""Execute the real manager class with fake HA service/state boundaries."""
import ast
import asyncio
import logging
import unittest
from typing import Optional, Any
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

source = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/__init__.py"
tree = ast.parse(source.read_text(encoding="utf-8"))
manager = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AutoApplyManager")
namespace = dict(HomeAssistant=object, Optional=Optional, Any=Any, _norm_instance_id=lambda x:x, DOMAIN="thermostat_timeline",
    asyncio=asyncio, _LOGGER=logging.getLogger(__name__),
    UnitOfTemperature=SimpleNamespace(FAHRENHEIT="F"),
    dt_util=SimpleNamespace(utcnow=lambda:datetime.now(timezone.utc)))
exec(compile(ast.Module(body=[manager], type_ignores=[]), str(source), "exec"), namespace)
Manager = namespace["AutoApplyManager"]

class AutoApplyTests(unittest.IsolatedAsyncioTestCase):
    def make(self, settings, state="off", attrs=None):
        entity = SimpleNamespace(state=state, attributes=attrs or {"hvac_modes":["off","heat"], "temperature":13})
        self.call = AsyncMock()
        states = {"climate.room":entity, "binary_sensor.summer":SimpleNamespace(state="on")}
        hass = SimpleNamespace(states=SimpleNamespace(get=states.get), services=SimpleNamespace(async_call=self.call),
            config=SimpleNamespace(units=SimpleNamespace(temperature_unit="C")),
            data={"thermostat_timeline":{"settings":settings,"schedules":{"climate.room":{}}}})
        return Manager(hass)

    async def test_disabled_turn_on_leaves_off_thermostat_off(self):
        mgr = self.make({"turn_on":{"climate.room":{"enabled":False}}})
        self.assertTrue(await mgr._apply_setpoint("climate.room",20))
        self.assertEqual([c.args[1] for c in self.call.await_args_list],["set_temperature"])

    async def test_enabled_turn_on_before_and_after_preserve_order(self):
        for order in ("before","after"):
            mgr = self.make({"turn_on":{"climate.room":{"enabled":True,"order":order}},"turn_on_delay_s":0})
            self.assertTrue(await mgr._apply_setpoint("climate.room",20))
            names = [c.args[1] for c in self.call.await_args_list]
            self.assertIn("set_hvac_mode",names)
            self.assertLess(names.index("set_hvac_mode"),names.index("set_temperature")) if order=="before" else self.assertGreater(names.index("set_hvac_mode"),names.index("set_temperature"))

    async def test_pause_sensor_blocks_timer_even_when_forced(self):
        mgr = self.make({"auto_apply_enabled":True,"pause_sensor_enabled":True,"pause_sensor_entity":"binary_sensor.summer"})
        await mgr._maybe_apply_now(force=True)
        await mgr.async_apply_entity_now("climate.room",reconcile=True)
        self.call.assert_not_awaited()
        self.assertFalse(mgr._auto_apply_enabled())

    async def test_boost_is_overridden_by_scheduled_manual_preset(self):
        mgr = self.make({},state="heat",attrs={"hvac_modes":["heat"],"preset_modes":["boost","manual"],"preset_mode":"boost"})
        self.assertTrue(await mgr._apply_setpoint("climate.room",20))
        self.assertEqual(self.call.await_args_list[0].args[2]["preset_mode"],"manual")


class ManualOverrideTests(unittest.IsolatedAsyncioTestCase):
    make = AutoApplyTests.make

    async def test_store_refresh_preserves_manual_override_until_desired_temperature_changes(self):
        mgr = self.make({'auto_apply_enabled': True, 'apply_on_edit': True}, state='heat')
        entity = mgr.hass.states.get('climate.room')
        entity.attributes['temperature'] = 21
        mgr._now_min = lambda: 14 * 60
        desired = {'value': 21}
        mgr._desired_for = lambda *args: desired['value']
        await mgr._maybe_apply_now(force=True)
        self.call.assert_not_awaited()
        self.assertEqual(mgr._last_applied['climate.room']['temp'], 21)
        entity.attributes['temperature'] = 22.5
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()
        for method in ('_reset_person_watch','_reset_boiler_watch','_reset_boiler_interval','_reset_pause_sensor_watch','_reset_target_recovery_watch'):
            setattr(mgr, method, lambda: None)
        await mgr._on_store_changed()
        self.call.assert_not_awaited()
        desired['value'] = 20
        await mgr._on_store_changed()
        self.call.assert_awaited()
        self.assertEqual(self.call.await_args.args[2]['temperature'], 20)

    async def test_normal_application_does_not_log_warning(self):
        mgr = self.make({}, state='heat')
        with self.assertNoLogs(namespace['_LOGGER'], level='WARNING'):
            self.assertTrue(await mgr._apply_setpoint('climate.room', 20))

if __name__ == '__main__':
    unittest.main()
