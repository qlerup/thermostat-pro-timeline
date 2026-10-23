"""Regression test for simultaneous room pause expirations."""

import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import test_auto_apply

class SimultaneousPauseExpiryTests(unittest.IsolatedAsyncioTestCase):
    make = test_auto_apply.AutoApplyTests.make

    async def test_cancelled_timer_callback_is_ignored(self):
        from unittest.mock import MagicMock
        from test_auto_apply import namespace

        mgr = self.make({"auto_apply_enabled": True})
        callbacks = []

        def fake_track(hass, callback_fn, when):
            callbacks.append(callback_fn)
            return MagicMock()

        mgr._next_room_pause_dt = MagicMock(return_value=(None, None))
        mgr._paused_until_dt = MagicMock(return_value=None)
        mgr._next_boundary_dt = MagicMock(
            return_value=datetime(2026, 10, 23, 13, 0, tzinfo=timezone.utc)
        )
        mgr._timer_fire = AsyncMock()
        mgr.hass.async_create_task = MagicMock(
            side_effect=lambda coro: asyncio.create_task(coro)
        )

        with patch.dict(namespace, {
            "async_track_point_in_utc_time": fake_track,
            "callback": lambda f: f,
            "dt_util": SimpleNamespace(
                utcnow=lambda: datetime.now(timezone.utc),
                as_utc=lambda dt: dt,
            ),
        }):
            await mgr._schedule_next()
            old_callback = callbacks[0]

            await mgr._schedule_next()
            new_callback = callbacks[1]

            old_callback(None)
            await asyncio.sleep(0)
            mgr._timer_fire.assert_not_awaited()

            new_callback(None)
            await asyncio.sleep(0)
            mgr._timer_fire.assert_awaited_once()

    async def test_obsolete_timer_generation_is_ignored(self):
        mgr = self.make({"auto_apply_enabled": True})

        mgr._timer_generation = 2
        mgr._next_room_resume = "climate.salon"

        mgr._apply_room_now = AsyncMock()
        mgr._maybe_apply_now = AsyncMock()
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()

        # Timer A belongs to generation 1.
        # Timer B (generation 2) has replaced it.
        await mgr._timer_fire(generation=1)

        mgr._apply_room_now.assert_not_awaited()
        mgr._maybe_apply_now.assert_not_awaited()
        mgr._maybe_control_boiler.assert_not_awaited()
        mgr._schedule_next.assert_not_awaited()

        # The current timer's state must remain intact.
        self.assertEqual(mgr._timer_generation, 2)
        self.assertEqual(
            mgr._next_room_resume,
            "climate.salon",
        )

    async def test_global_pause_blocks_room_reconciliation(self):
        from datetime import timedelta
        from test_auto_apply import namespace

        expiry = datetime(2026, 10, 23, 12, 1, tzinfo=timezone.utc)

        settings = {
            "auto_apply_enabled": True,
            "pause_indef": True,
            "room_pause": {
                "climate.room": {
                    "indef": False,
                    "until_ms": expiry.timestamp() * 1000,
                }
            },
        }

        mgr = self.make(settings)
        mgr._next_room_resume = "climate.room"
        mgr._next_room_resume_at = expiry
        mgr._next_is_resume = False
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()

        fake_dt_util = SimpleNamespace(
            utcnow=lambda: expiry + timedelta(seconds=1),
        )

        with patch.dict(namespace, {"dt_util": fake_dt_util}):
            await mgr._timer_fire()

        self.call.assert_not_awaited()

    async def test_late_timer_resumes_all_matching_rooms(self):
        from datetime import timedelta
        from test_auto_apply import namespace

        now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        expiry = now + timedelta(minutes=1)

        settings = {
            "room_pause": {
                eid: {
                    "indef": False,
                    "until_ms": expiry.timestamp() * 1000,
                }
                for eid in ("climate.salon", "climate.chambre")
            }
        }

        mgr = self.make(settings)
        mgr._next_room_resume = "climate.salon"
        mgr._next_room_resume_at = expiry
        mgr._next_is_resume = False

        resumed = []

        async def fake_apply_room(eid):
            resumed.append(eid)

        mgr._apply_room_now = fake_apply_room
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()

        fake_dt_util = SimpleNamespace(
            utcnow=lambda: expiry + timedelta(seconds=5),
        )

        with patch.dict(namespace, {"dt_util": fake_dt_util}):
            await mgr._timer_fire()

        self.assertCountEqual(
            resumed,
            ["climate.salon", "climate.chambre"],
        )

    async def test_extended_pause_is_not_resumed_early(self):
        from datetime import timedelta
        from test_auto_apply import namespace

        now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        expiry = now + timedelta(minutes=1)

        settings = {
            "room_pause": {
                "climate.salon": {
                    "indef": False,
                    "until_ms": expiry.timestamp() * 1000,
                },
                "climate.chambre": {
                    "indef": False,
                    "until_ms": (
                        expiry + timedelta(minutes=29)
                    ).timestamp() * 1000,
                },
            }
        }

        mgr = self.make(settings)
        mgr._next_room_resume = "climate.salon"
        mgr._next_room_resume_at = expiry
        mgr._next_is_resume = False

        resumed = []

        async def fake_apply_room(eid):
            resumed.append(eid)

        mgr._apply_room_now = fake_apply_room
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()

        fake_dt_util = SimpleNamespace(
            utcnow=lambda: expiry,
        )

        with patch.dict(namespace, {"dt_util": fake_dt_util}):
            await mgr._timer_fire()

        self.assertEqual(resumed, ["climate.salon"])





    async def test_timer_reconciles_all_due_rooms_only(self):
        from datetime import timedelta
        from unittest.mock import patch
        from test_auto_apply import namespace

        now = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
        expiry = now + timedelta(minutes=1)

        settings = {
            "room_pause": {
                "climate.salon": {
                    "indef": False,
                    "until_ms": expiry.timestamp() * 1000,
                },
                "climate.chambre": {
                    "indef": False,
                    "until_ms": expiry.timestamp() * 1000,
                },
                "climate.bureau": {
                    "indef": False,
                    "until_ms": (expiry + timedelta(minutes=10)).timestamp() * 1000,
                },
                "climate.cuisine": {
                    "indef": True,
                    "until_ms": 0,
                },
            }
        }

        mgr = self.make(settings)
        clock = {"now": now}

        fake_dt_util = SimpleNamespace(
            utcnow=lambda: clock["now"],
            utc_from_timestamp=lambda ts: datetime.fromtimestamp(
                ts, timezone.utc
            ),
        )

        resumed = []

        async def fake_apply_room(eid):
            resumed.append(eid)

        mgr._apply_room_now = fake_apply_room
        mgr._maybe_control_boiler = AsyncMock()
        mgr._schedule_next = AsyncMock()

        with patch.dict(namespace, {"dt_util": fake_dt_util}):
            wake, room = mgr._next_room_pause_dt()

            self.assertEqual(wake, expiry)
            self.assertEqual(room, "climate.salon")

            mgr._next_room_resume = room
            mgr._next_room_resume_at = wake
            mgr._next_is_resume = False

            clock["now"] = expiry

            await mgr._timer_fire()

        self.assertCountEqual(
            resumed,
            ["climate.salon", "climate.chambre"],
        )

if __name__ == "__main__":
    unittest.main()
