"""Regression tests for the state feedback used during seasonal handovers."""
import ast
import math
import unittest
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock


def load_controller():
    path = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/seasonal_sources.py"
    tree = ast.parse(path.read_text())
    tree.body = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    namespace = {"callback": lambda method: method, "Store": Mock, "DOMAIN": "timeline",
                 "math": math, "monotonic": monotonic}
    exec(compile(tree, str(path), "exec"), namespace)
    return namespace["SeasonalSources"]


class SeasonalHandoverTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.old, self.new = "climate.boiler", "climate.pump"
        self.states = {}
        self.calls = []
        self.rules = {"enabled": True, "winter": {"entity": self.old, "mode": "heat"},
                      "summer": {"entity": self.new, "mode": "cool", "target_c": 20}}
        self.settings = {"seasonal_enabled": True, "season": "summer", "seasonal_sources": self.rules}
        manager = Mock()
        manager._get_data.return_value = {}, self.settings
        manager._all_targets.return_value = set()
        manager._season_key.side_effect = lambda settings: settings["season"]
        hass = SimpleNamespace(data={"timeline": {}}, states=self.states,
                               config=SimpleNamespace(units=SimpleNamespace(temperature_unit="C")),
                               services=SimpleNamespace(async_call=self.command))
        self.controller = load_controller()(hass, None, {"default": manager})
        self.controller.watch = Mock()
        self.controller.store = SimpleNamespace(async_save=AsyncMock())
        self.report(self.old, "heat")
        self.report(self.new, "off")

    async def command(self, domain, service, fields, blocking):
        self.calls.append((fields["entity_id"], fields.get("hvac_mode", fields.get("temperature"))))

    def report(self, entity, mode, temperature=17):
        self.states[entity] = SimpleNamespace(state=mode, last_reported=object(), attributes={
            "hvac_modes": ["heat", "cool", "off"], "supported_features": 1, "temperature": temperature,
            "min_temp": 5, "max_temp": 90})

    async def test_only_advance_when_devices_report_expected_modes(self):
        await self.controller.reconcile()
        await self.controller.reconcile()
        self.assertEqual(self.calls, [(self.old, "off")])
        self.report(self.old, "unavailable")
        await self.controller.reconcile()
        self.assertEqual(len(self.calls), 1)
        self.report(self.old, "off")
        await self.controller.reconcile()
        self.assertEqual(self.calls[-1], (self.new, "cool"))
        self.report(self.new, "cool")
        await self.controller.reconcile()
        self.assertEqual(self.calls[-1], (self.new, 20))
        self.report(self.new, "cool", 20)
        await self.controller.reconcile()
        self.report(self.new, "cool", 19)
        await self.controller.reconcile()
        self.assertEqual(len(self.calls), 3)

    async def test_reverse_while_start_is_unconfirmed(self):
        self.report(self.old, "off")
        await self.controller.reconcile()
        self.settings["season"] = "winter"
        await self.controller.reconcile()
        await self.controller.reconcile()
        self.assertEqual(self.calls, [(self.new, "cool"), (self.new, "off")])
        self.report(self.new, "off")
        await self.controller.reconcile()
        self.assertEqual(self.calls[-1], (self.old, "heat"))

    async def test_reversible_unit_and_fahrenheit(self):
        self.rules["summer"]["entity"] = self.old
        self.controller.hass.config.units.temperature_unit = "F"
        await self.controller.reconcile()
        self.assertEqual(self.calls, [(self.old, "off")])
        self.report(self.old, "off")
        await self.controller.reconcile()
        self.report(self.old, "cool")
        await self.controller.reconcile()
        self.assertEqual(self.calls, [(self.old, "off"), (self.old, "cool"), (self.old, 68)])

    async def test_replaced_source_must_also_stop_after_restart(self):
        former = "climate.previous"
        self.controller.owner = {"entity": former, "starting": False}
        self.report(self.old, "off")
        await self.controller.reconcile()
        self.assertFalse(self.calls)
        self.report(former, "heat")
        await self.controller.reconcile()
        self.assertEqual(self.calls, [(former, "off")])
        self.report(former, "off")
        await self.controller.reconcile()
        self.assertEqual(self.calls[-1], (self.new, "cool"))

    async def test_no_commands_for_disabled_invalid_or_room_sources(self):
        self.rules["enabled"] = False
        await self.controller.reconcile()
        self.rules["enabled"] = True
        self.rules["summer"]["target_c"] = 150
        await self.controller.reconcile()
        self.rules["summer"].pop("target_c")
        self.settings["entities"] = [self.new]
        await self.controller.reconcile()
        self.assertFalse(self.calls)
