"""Pagination settings through the real admin handler, settings manager, and player API.

Run: .venv/Scripts/python -m unittest discover -s tests -p test_music_pagination_settings.py -v
Unrelated Telegram service imports are excluded when compiling production definitions.
"""

import ast
import asyncio
import copy
import secrets
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import Mock

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def definitions(filename, names, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if getattr(node, "name", None) in names
             or isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in names]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), filename, "exec"), namespace)
    return namespace


def settings_runtime():
    return definitions("Backend/helper/settings_manager.py", {"_DEFAULTS", "_seed_from_env", "Settings", "SettingsManager"}, {
        "Any": Any, "Dict": Dict, "List": List, "secrets": secrets,
        "botmod": types.SimpleNamespace(Userbot=None, StreamBot=None), "LOGGER": Mock(),
    })


class Database:
    def __init__(self):
        self.document = {"session_secret": "test-secret", "admin_password": "private-test-value", "audio_cache_size_gb": 5}
        self.writes = 0

    async def get_settings(self):
        return copy.deepcopy(self.document)

    async def save_settings(self, data):
        self.document = copy.deepcopy(data)
        self.writes += 1


def fixture():
    runtime = settings_runtime()
    database = Database()
    manager = runtime["SettingsManager"]
    manager._current = runtime["Settings"](database.document)
    namespace = {"SettingsManager": manager, "db": database, "HTTPException": HTTPException, "LOGGER": Mock()}
    definitions("Backend/fastapi/routes/api_routes.py", {"update_settings_api"}, namespace)
    app = FastAPI()

    async def require_admin(request: Request):
        if request.headers.get("x-test-admin") != "1":
            raise HTTPException(status_code=401)
        return True

    # Compile the existing protected route as well as its implementation.
    definitions("Backend/fastapi/main.py", {"update_settings"}, {
        "app": app, "Depends": Depends, "require_auth": require_admin,
        "update_settings_api": namespace["update_settings_api"],
    })
    router = APIRouter()
    definitions("Backend/fastapi/routes/music/settings.py", {"get_music_player_settings"}, {
        "router": router, "SettingsManager": manager, "JSONResponse": JSONResponse,
    })
    app.include_router(router)
    return app, database, manager


class MusicPaginationSettingsTests(unittest.TestCase):
    def setUp(self):
        self.app, self.db, self.manager = fixture()
        self.client = self.enterContext(TestClient(self.app))

    def save(self, payload):
        return self.client.put("/api/admin/settings", json=payload, headers={"x-test-admin": "1"})

    def test_old_install_defaults_and_public_response_do_not_expose_secrets(self):
        response = self.client.get("/api/music/player-settings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success", "settings": {
            "music_tracklist_page_size": 60, "music_mobile_tracklist_page_size": 50,
        }})
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(self.db.writes, 0)

    def test_only_admin_can_change_pagination(self):
        response = self.client.put("/api/admin/settings", json={"music_tracklist_page_size": 100})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.db.writes, 0)

    def test_saved_sizes_survive_reload_and_preserve_other_settings(self):
        payload = {"music_tracklist_page_size": 30, "music_mobile_tracklist_page_size": 20}
        self.assertEqual(self.save(payload).status_code, 200)
        self.assertEqual(self.client.get("/api/music/player-settings").json()["settings"], payload)
        self.assertEqual(self.db.document["audio_cache_size_gb"], 5)
        self.assertEqual(self.db.document["admin_password"], "private-test-value")
        self.manager._current = None
        asyncio.run(self.manager.initialize(self.db))
        self.assertEqual(self.client.get("/api/music/player-settings").json()["settings"], payload)

    def test_invalid_sizes_fail_atomically(self):
        for key in ("music_tracklist_page_size", "music_mobile_tracklist_page_size"):
            for value in (0, 9, 201, 100000, -1, 40.5, "20.5", None, True, [], {}, "all"):
                with self.subTest(key=key, value=value):
                    payload = {"music_tracklist_page_size": 30, "music_mobile_tracklist_page_size": 20, key: value}
                    self.assertEqual(self.save(payload).status_code, 400)
        self.assertEqual(self.db.writes, 0)
        self.assertEqual(self.manager.current().music_tracklist_page_size, 60)

    def test_bounds_and_numeric_strings(self):
        response = self.save({"music_tracklist_page_size": "10", "music_mobile_tracklist_page_size": "200"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/music/player-settings").json()["settings"], {
            "music_tracklist_page_size": 10, "music_mobile_tracklist_page_size": 200,
        })

    def test_malformed_stored_values_fall_back_to_bounded_defaults(self):
        snapshot_class = self.manager.current().__class__
        for value in (0, 9, 100000, True, 40.5, None, "invalid"):
            self.manager._current = snapshot_class({"music_tracklist_page_size": value, "music_mobile_tracklist_page_size": value})
            self.assertEqual(self.client.get("/api/music/player-settings").json()["settings"], {
                "music_tracklist_page_size": 60, "music_mobile_tracklist_page_size": 50,
            })


if __name__ == "__main__":
    unittest.main()
