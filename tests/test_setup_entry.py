"""Regression test for starting the integration with saved backup slots."""

import ast
import logging
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from test_seasonal_sources import load_controller


class SetupEntryTests(unittest.IsolatedAsyncioTestCase):
    async def test_populated_backups_preserve_config_entry_during_setup(self):
        path = Path(__file__).resolve().parents[1] / "custom_components/thermostat_timeline/__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        setup = next(node for node in tree.body
                     if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_setup_entry")
        tree.body = [*ast.parse("from __future__ import annotations").body, setup]

        slot = {"schedules": {"climate.living_room": []}}
        store = Mock(side_effect=[
            SimpleNamespace(async_load=AsyncMock(return_value={})),
            SimpleNamespace(async_load=AsyncMock(return_value={"slots": ["invalid", slot]})),
        ])
        entry = Mock(spec=["async_on_unload"])
        manager = SimpleNamespace(async_start=AsyncMock())
        room_air = Mock(return_value=SimpleNamespace(load=AsyncMock(), start=Mock()))
        startup_manager = Mock(return_value=manager)
        seasonal_sources = load_controller(Mock(), Mock())
        hass = SimpleNamespace(data={}, services=Mock(), http=Mock())
        namespace = {
            "__package__": "",
            "Store": store,
            "DOMAIN": "timeline",
            "STORAGE_VERSION": 1,
            "STORAGE_KEY": "timeline",
            "BACKUP_STORAGE_KEY": "timeline_backup",
            "_dbg": Mock(),
            "_norm_instance_id": lambda value: value,
            "_LOGGER": logging.getLogger(__name__),
            "vol": Mock(),
            "cv": Mock(),
            "ThermostatTimelineStateView": Mock(),
            "ThermostatTimelineVersionView": Mock(),
            "MultiInstanceAutoApplyManager": startup_manager,
            "RoomAir": room_air,
            "SeasonalSources": seasonal_sources,
            "MultiInstanceOpenWindowManager": startup_manager,
            "MultiInstancePresenceSensorManager": startup_manager,
            "BackupManager": startup_manager,
            "ThermalControl": Mock(return_value=SimpleNamespace(start=AsyncMock())),
        }
        exec(compile(tree, str(path), "exec"), namespace)

        with patch.dict(seasonal_sources.start.__globals__, {
            "Store": Mock(return_value=SimpleNamespace(async_load=AsyncMock(return_value={}))),
            "SIGNAL_UPDATED": "timeline_updated",
            "async_dispatcher_connect": Mock(),
            "async_track_time_interval": Mock(),
            "timedelta": timedelta,
        }), patch.object(seasonal_sources, "wake"):
            self.assertTrue(await namespace["async_setup_entry"](hass, entry))

        self.assertEqual(hass.data["timeline"]["backup_slots"], [None, slot])
        self.assertEqual(hass.data["timeline"]["backup_slot_index"], 1)
        room_air.assert_called_once_with(hass, entry, manager)
        self.assertEqual(entry.async_on_unload.call_count, 3)
