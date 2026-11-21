"""Exercise the channel-list HTTP handler without starting Telegram services.

Run: .venv/Scripts/python -m unittest discover -s tests -p test_music_channels.py -v
"""

import ast
import asyncio
import copy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = [
    {"id": "-100123", "name": "Nhạc Việt", "username": "nhacviet",
     "last_scanned_id": 42, "last_scanned_at": "10:00 10/11/2026",
     "total_tracks": 12, "auto_sync": True},
    {"chat_id": "-100456", "name": "Lossless", "total_tracks": "3"},
]


def fixture(saved=None):
    router = APIRouter()
    channels = copy.deepcopy(CHANNELS if saved is None else saved)
    load = AsyncMock(return_value=channels)
    telegram = types.SimpleNamespace(get_chat=AsyncMock(
        return_value=types.SimpleNamespace(title="Live title", username="live")))

    async def require_admin(request: Request):
        if request.headers.get("x-test-admin") != "1":
            raise HTTPException(status_code=401, detail="Not authenticated")
        return True

    namespace = {
        "router": router, "Depends": Depends, "require_auth": require_admin,
        "_db_load_channels": load, "_get_active_client": Mock(return_value=telegram),
        "asyncio": asyncio, "HTTPException": HTTPException, "LOGGER": Mock(),
    }
    filename = "Backend/fastapi/routes/music/scan.py"
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if getattr(node, "name", None) == "get_music_channels"
             or isinstance(node, ast.Assign) and any(
                 getattr(target, "id", None) == "_CHANNELS_LOAD_TIMEOUT" for target in node.targets)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), namespace)
    namespace["_CHANNELS_LOAD_TIMEOUT"] = 0.02
    app = FastAPI()
    app.include_router(router)
    return app, namespace, load, telegram, channels


class MusicChannelTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app, self.namespace, self.load, self.telegram, self.channels = fixture()
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app), base_url="http://test")
        self.addAsyncCleanup(self.client.aclose)

    async def get_channels(self):
        # A broken handler fails quickly rather than hanging the test process.
        return await asyncio.wait_for(
            self.client.get("/api/music/channels", headers={"x-test-admin": "1"}), 0.3)

    async def test_saved_channel_metadata_and_progress_are_preserved(self):
        response = await self.get_channels()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "channels": [
            CHANNELS[0],
            {"id": "-100456", "name": "Lossless", "username": "",
             "last_scanned_id": 0, "last_scanned_at": "", "total_tracks": 3, "auto_sync": False},
        ]})
        self.telegram.get_chat.assert_not_awaited()

    async def test_unresponsive_telegram_does_not_block_the_channel_list(self):
        async def unavailable(*args):
            await asyncio.Event().wait()

        self.telegram.get_chat.side_effect = unavailable
        response = await self.get_channels()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["channels"]), 2)
        self.telegram.get_chat.assert_not_awaited()

    async def test_storage_timeout_returns_json_service_error(self):
        cancelled = asyncio.Event()

        async def unavailable():
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

        self.load.side_effect = unavailable
        response = await self.get_channels()
        self.assertEqual(response.status_code, 503)
        self.assertIn("application/json", response.headers["content-type"])
        self.assertIn("thử lại", response.json()["detail"])
        self.assertTrue(cancelled.is_set())
        self.telegram.get_chat.assert_not_awaited()

    async def test_admin_auth_is_still_required(self):
        response = await self.client.get("/api/music/channels")
        self.assertEqual(response.status_code, 401)
        self.load.assert_not_awaited()

    async def test_settings_fallback_does_not_modify_the_saved_channel_cache(self):
        self.load.return_value = []
        settings = types.SimpleNamespace(SettingsManager=types.SimpleNamespace(
            current=lambda: types.SimpleNamespace(auth_channels=[-100789])))
        with patch.dict(sys.modules, {"Backend.helper.settings_manager": settings}):
            response = await self.get_channels()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["channels"][0]["id"], "-100789")
        self.assertEqual(self.load.return_value, [])
        self.telegram.get_chat.assert_not_awaited()

    async def test_empty_configuration_returns_an_empty_list(self):
        self.load.return_value = []
        settings = types.SimpleNamespace(SettingsManager=types.SimpleNamespace(
            current=lambda: types.SimpleNamespace(auth_channels=[])))
        with patch.dict(sys.modules, {"Backend.helper.settings_manager": settings}):
            response = await self.get_channels()
        self.assertEqual(response.json(), {"status": "success", "channels": []})


if __name__ == "__main__":
    unittest.main()
