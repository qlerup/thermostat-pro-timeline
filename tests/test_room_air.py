"""Room air regressions that can run outside a Home Assistant installation."""

import ast
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock


def load_rules():
    path = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/room_air.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tree.body = [item for item in tree.body if isinstance(item, (ast.ClassDef, ast.FunctionDef))]
    scope = {
        "numeric": lambda v: None if v is None else float(v),
        "callback": lambda f: f,
        "Store": Mock,
        "DOMAIN": "thermostat_timeline",
    }
    exec(compile(tree, str(path), "exec"), scope)
    return scope


class RoomAirTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.scope = load_rules()
        self.now = datetime.now(timezone.utc)
        self.states = {}
        hass = SimpleNamespace(states=self.states, services=SimpleNamespace(async_call=AsyncMock()))
        self.air = self.scope["RoomAir"](hass, Mock(), {})

    def test_cap_and_cooling(self):
        adjust = self.scope["adjustment"]
        r = {"boost": 3, "cap": 23, "eco_delta": 1}
        self.assertEqual(adjust(r, "comfort", "heat", 22, 20), (1, True))
        self.assertEqual(adjust(r, "comfort", "heat", 22, 24), (0, True))
        for action, fan in [("skip", False), ("fan_only", True)]:
            self.assertEqual(adjust({**r, "cap_action": action}, "comfort", "heat", 22), (0, fan))
        self.assertEqual(adjust(r, "comfort", "cool", 22), (-3, True))
        self.assertEqual(adjust(r, "eco", "cool", 22), (1, True))
        self.assertEqual(adjust(r, "comfort", "off", 22), (0, True))

    def test_fan_priority(self):
        choose = self.scope["choose_speed"]
        r = {
            "default_speed": "off",
            "targets": [{"at": 20, "speed": "auto"}],
            "smart": [{"at": 3, "speed": "high"}, {"at": 1, "speed": "medium"}],
            "comfort_speed": "low",
            "night_speed": "sleep",
        }
        self.assertEqual(choose(r, {}, 0, 21, "schedule", True, False), "auto")
        self.assertEqual(choose(r, {}, 3, 21, "schedule", True, False), "high")
        block = {"fan_speed": "medium"}
        self.assertEqual(choose(r, block, 3, 21, "comfort", False, False), "medium")
        self.assertEqual(choose(r, block, 3, 21, "comfort", True, False), "low")
        self.assertEqual(choose(r, block, 3, 21, "comfort", True, True), "sleep")
        night = self.scope["night_time"]
        self.assertTrue(night({"night": True}, 40))
        self.assertFalse(night({"night": True}, 12 * 60))

    def test_presence_debounce_alarm_and_expiry(self):
        r = {"presence": True, "sensor": "occ", "on_s": 30, "off_s": 60, "boost_minutes": 1}

        def sense(state, ago):
            self.states["occ"] = SimpleNamespace(state=state, last_changed=self.now - timedelta(seconds=ago))
            return self.air.profile("office", r, 600, self.now)[0]

        self.assertEqual(sense("off", 80), "eco")
        self.assertEqual(sense("on", 15), "eco")
        self.assertEqual(sense("on", 30), "comfort")
        self.assertEqual(sense("on", 90), "schedule")
        self.assertEqual(sense("unavailable", 0), "schedule")
        r.update(profile="night", alarm="alarm")
        self.assertEqual(sense("on", 31), "alarm")
        r["alarm_eco"] = True
        self.states["alarm"] = SimpleNamespace(state="armed_away")
        self.assertEqual(sense("on", 31), "alarm_eco")
        self.states["alarm"].state = "disarmed"
        self.assertEqual(sense("on", 31), "night")

    async def test_restore_only_our_fan_setting(self):
        st = SimpleNamespace(
            state="heat", attributes={"fan_mode": "auto", "fan_modes": ["auto", "low", "high"]}
        )
        self.states["climate.office"] = st
        await self.air.speed("key", "climate.office", "high", False)
        self.assertEqual(self.air.baselines["key"]["before"], "auto")
        st.attributes["fan_mode"] = "low"
        self.air.hass.services.async_call.reset_mock()
        await self.air.speed("key", "climate.office", "", False)
        self.air.hass.services.async_call.assert_not_awaited()
        self.assertNotIn("key", self.air.baselines)

    def test_history_is_bounded_and_only_read_for_one_room(self):
        status = self.air.status.setdefault("default", {})
        for i in range(70):
            self.air.publish("default/office", "office", status, "schedule", str(i), None, self.now)
        self.assertNotIn("history", self.air.snapshot("default")["office"])
        history = self.air.snapshot("default", "office")["history"]
        self.assertEqual(len(history), 50)
        self.assertEqual(history[0]["reason"], "20")
