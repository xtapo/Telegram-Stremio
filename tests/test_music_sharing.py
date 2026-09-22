"""Sharing API integration tests without MongoDB or Telegram credentials.

Run: .venv/Scripts/python -m unittest discover -s tests -p test_music_sharing.py -v
Run the isolated browser fixture: .venv/Scripts/python tests/test_music_sharing.py --serve
"""

import copy
import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


class Cursor:
    def __init__(self, documents):
        self.documents = documents

    def sort(self, fields):
        for key, direction in reversed(fields):
            self.documents.sort(key=lambda doc: doc[key], reverse=direction == -1)
        return self

    def skip(self, offset):
        self.documents = self.documents[offset:]
        return self

    def limit(self, limit):
        self.documents = self.documents[:limit]
        return self

    async def to_list(self, length):
        return copy.deepcopy(self.documents[:length])


class Collection:
    """Small Mongo-style store for the query/update operations under test."""
    def __init__(self, documents=()):
        self.documents = copy.deepcopy(list(documents))

    def matches(self, doc, query):
        for key, expected in query.items():
            value = [p.get(key.split(".", 1)[1]) for p in doc.get("playlists", [])] if key.startswith("playlists.") else doc.get(key)
            if isinstance(expected, dict):
                if "$regex" in expected:
                    if not re.search(expected["$regex"], value or "", re.I):
                        return False
                elif "$ne" in expected:
                    if expected["$ne"] in value:
                        return False
                elif "$exists" in expected:
                    if (key in doc) != expected["$exists"]:
                        return False
                else:
                    raise AssertionError(f"Unsupported query: {expected}")
            elif value != expected:
                return False
        return True

    async def find_one(self, query):
        return copy.deepcopy(next((d for d in self.documents if self.matches(d, query)), None))

    def find(self, query, projection=None):
        docs = copy.deepcopy([d for d in self.documents if self.matches(d, query)])
        for doc in docs:
            for field, include in (projection or {}).items():
                if not include:
                    doc.pop(field, None)
        return Cursor(docs)

    async def insert_one(self, doc):
        self.documents.append(copy.deepcopy(doc))

    async def update_one(self, query, update, upsert=False):
        doc = next((d for d in self.documents if self.matches(d, query)), None)
        if doc is None and not upsert:
            return types.SimpleNamespace(modified_count=0)
        if doc is None:
            doc = {"_id": query["_id"], **copy.deepcopy(update.get("$setOnInsert", {}))}
            self.documents.append(doc)
        previous = copy.deepcopy(doc)
        doc.update(copy.deepcopy(update.get("$set", {})))
        for key, value in update.get("$push", {}).items():
            doc.setdefault(key, []).append(copy.deepcopy(value))
        return types.SimpleNamespace(modified_count=int(previous != doc))

    async def delete_one(self, query):
        count = len(self.documents)
        self.documents = [d for d in self.documents if not self.matches(d, query)]
        return types.SimpleNamespace(deleted_count=count - len(self.documents))


def load_routes(database):
    backend = types.ModuleType("Backend")
    backend.db = database
    credentials = types.ModuleType("Backend.fastapi.security.credentials")
    credentials.require_auth = lambda: True
    passwords = types.ModuleType("Backend.helper.passwords")
    passwords.hash_password = passwords.verify_password = Mock()
    modules = {"Backend": backend, credentials.__name__: credentials, passwords.__name__: passwords}

    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, ROOT / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with patch.dict(sys.modules, modules):
        auth = load("sharing_test_auth", "Backend/fastapi/routes/music_auth.py")
        with patch.dict(sys.modules, {"Backend.fastapi.routes.music_auth": auth}):
            sharing = load("sharing_test_routes", "Backend/fastapi/routes/music_sharing.py")
    return auth, sharing


def fixture():
    track = {"name": "Bình minh", "artist": "Nghệ sĩ thử nghiệm", "chatId": "-100123", "msgId": "42", "duration": "3:24", "coverUrl": "/music/icon-192.png"}
    favorite = {"title": track["name"], "artist": track["artist"], "chat_id": -100123, "msg_id": 42, "cover_url": track["coverUrl"]}
    users = Collection([
        {"_id": name, "username": name, "display_name": name.title(), "is_active": name != "blocked", "avatar_url": "/music/icon-192.png"}
        for name in ["alice", "bob", "eve", "blocked", "a.b"]
    ])
    data = Collection([
        {"_id": "alice", "playlists": [{"id": "pl_alice", "name": "Nhạc chill buổi sáng", "tracks": [track]}], "favorites": [favorite]},
        {"_id": "bob", "playlists": [{"id": "pl_bob", "name": "Nhạc của Bob", "tracks": [track]}], "favorites": []},
    ])
    shares = Collection()
    database = types.SimpleNamespace(dbs={"tracking": {"music_users": users, "music_user_data": data, "music_user_shares": shares}})
    auth, sharing = load_routes(database)
    app = FastAPI()

    @app.middleware("http")
    async def test_session(request, call_next):
        user = request.headers.get("x-test-user") or request.cookies.get("test_user")
        request.scope["session"] = {"music_user_id": user} if user else {}
        return await call_next(request)

    app.include_router(sharing.router)
    # Only these existing library routes are needed in the isolated UI fixture.
    for route in auth.auth_router.routes:
        if route.path in ("/api/music/user/favorites", "/api/music/user/playlists"):
            app.router.routes.append(route)

    @app.get("/api/music/auth/profile")
    async def profile(request: Request):
        user = await users.find_one({"_id": request.session.get("music_user_id")})
        return {"status": "authenticated" if user else "guest", "user": user}

    @app.get("/api/music/albums")
    async def albums():
        return {"status": "success", "albums": [{"id": "demo", "title": "Album thử nghiệm", "artist": track["artist"], "coverUrl": "/music/icon-192.png", "tracks": [track]}]}

    @app.get("/fixture/{username}")
    async def switch_test_account(username: str):
        response = FileResponse(ROOT / "Music/index.html")
        response.set_cookie("test_user", username)
        return response

    @app.get("/api/music/stream/{chat_id}/{msg_id}")
    async def sample_audio(chat_id: str, msg_id: str):
        # Local silence lets browser tests verify the player without Telegram access.
        import io
        import wave
        from fastapi.responses import Response
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b"\x00\x00" * 8000 * 10)
        return Response(buffer.getvalue(), media_type="audio/wav")

    app.mount("/music", StaticFiles(directory=ROOT / "Music", html=True))
    return app, database, sharing


class MusicSharingTests(unittest.TestCase):
    def setUp(self):
        self.app, self.db, self.routes = fixture()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.data = self.db.dbs["tracking"]["music_user_data"]
        self.shares = self.db.dbs["tracking"]["music_user_shares"]

    def call(self, method, path="", user="alice", **kwargs):
        return self.client.request(method, "/api/music/user/shares" + path, headers={"x-test-user": user} if user else {}, **kwargs)

    def send(self, **overrides):
        return self.call("POST", json={"recipient": "bob", "kind": "playlist", "playlist_id": "pl_alice", **overrides})

    def test_snapshot_survives_source_change_and_only_recipient_can_read(self):
        response = self.send(recipient=" @BOB ")
        self.assertEqual(response.status_code, 200)
        share_id = response.json()["share_id"]
        self.data.documents[0]["playlists"][0]["tracks"].clear()
        inbox = self.call("GET", user="bob").json()
        self.assertEqual(len(inbox["shares"]), 1)
        self.assertNotIn("tracks", inbox["shares"][0])
        self.assertNotIn("recipient_id", inbox["shares"][0])
        self.assertEqual(self.call("GET", user="eve").json()["shares"], [])
        detail = self.call("GET", f"/{share_id}", user="bob").json()["share"]
        self.assertEqual(detail["tracks"][0]["previewUrl"], "/api/music/stream/-100123/42")
        for user in ("eve", "alice"):
            self.assertEqual(self.call("GET", f"/{share_id}", user=user).status_code, 404)
            self.assertEqual(self.call("POST", f"/{share_id}/import", user=user, json={"destination": "playlist"}).status_code, 404)
            self.assertEqual(self.call("DELETE", f"/{share_id}", user=user).status_code, 404)

    def test_authentication_required_for_all_actions(self):
        share_id = self.send().json()["share_id"]
        for user, status in [(None, 401), ("blocked", 403), ("deleted", 403)]:
            for method, path, payload in [
                ("GET", "", None), ("GET", f"/{share_id}", None),
                ("POST", "", {"recipient": "bob", "kind": "favorites"}),
                ("POST", f"/{share_id}/import", {"destination": "favorites"}),
                ("DELETE", f"/{share_id}", None),
            ]:
                self.assertEqual(self.call(method, path, user=user, json=payload).status_code, status)

    def test_source_ownership_recipient_validation_and_empty_selection(self):
        self.assertEqual(self.send(playlist_id="pl_bob").status_code, 404)
        for recipient in ("missing", "blocked", ".*"):
            self.assertEqual(self.send(recipient=recipient).status_code, 404)
        self.assertEqual(self.send(recipient="alice").status_code, 400)
        self.assertEqual(self.send(recipient=" @ ").status_code, 400)
        self.assertEqual(self.send(recipient="a.b").status_code, 200)
        self.data.documents[0]["playlists"][0]["tracks"] = []
        self.assertEqual(self.send().status_code, 400)
        self.assertEqual(self.send(tracks=[{"name": "forged"}]).status_code, 422)
        self.assertEqual(self.send(kind="invalid").status_code, 422)

    def test_share_all_or_single_favorite_uses_full_track_identity(self):
        self.data.documents[0]["favorites"].append({"title": "Same message, different chat", "chat_id": -100999, "msg_id": 42})
        single = self.call("POST", json={"recipient": "bob", "kind": "favorites", "favorite": {"chat_id": "-100123", "msg_id": "42"}})
        self.assertEqual(single.status_code, 200)
        self.assertEqual(self.shares.documents[0]["track_count"], 1)
        all_favorites = self.call("POST", json={"recipient": "bob", "kind": "favorites"})
        self.assertEqual(all_favorites.status_code, 200)
        self.assertEqual(self.shares.documents[1]["track_count"], 2)
        missing = self.call("POST", json={"recipient": "bob", "kind": "favorites", "favorite": {"chat_id": "-1", "msg_id": "42"}})
        self.assertEqual(missing.status_code, 404)

    def test_import_is_repeatable_and_preserves_existing_library(self):
        share_id = self.send().json()["share_id"]
        for _ in range(2):
            self.assertEqual(self.call("POST", f"/{share_id}/import", user="bob", json={"destination": "playlist"}).status_code, 200)
        bob = self.data.documents[1]
        self.assertEqual(len(bob["playlists"]), 2)
        self.assertEqual(bob["playlists"][0]["id"], "pl_bob")
        bob["playlists"][1]["name"] = "My edited copy"
        self.call("POST", f"/{share_id}/import", user="bob", json={"destination": "playlist"})
        self.assertEqual(bob["playlists"][1]["name"], "My edited copy")
        bob["favorites"] = [{"title": "Keep me", "chat_id": -100999, "msg_id": 42}]
        for expected in (1, 0):
            result = self.call("POST", f"/{share_id}/import", user="bob", json={"destination": "favorites"})
            self.assertEqual(result.json()["added_count"], expected)
        self.assertEqual(len(bob["favorites"]), 2)
        self.assertEqual(bob["favorites"][0]["title"], "Keep me")
        self.assertEqual(self.call("DELETE", f"/{share_id}", user="bob").status_code, 200)
        self.assertEqual(len(bob["playlists"]), 2)
        self.assertEqual(len(bob["favorites"]), 2)
        self.assertEqual(self.call("GET", f"/{share_id}", user="bob").status_code, 404)

    def test_favorite_import_retries_concurrent_change(self):
        share_id = self.send().json()["share_id"]
        update = self.data.update_one
        conflict = {"title": "Added concurrently", "chat_id": -22, "msg_id": 8}
        async def race(query, changes, upsert=False):
            if "favorites" in query and not self.data.documents[1]["favorites"]:
                self.data.documents[1]["favorites"].append(conflict)
            return await update(query, changes, upsert)
        with patch.object(self.data, "update_one", race):
            result = self.call("POST", f"/{share_id}/import", user="bob", json={"destination": "favorites"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.data.documents[1]["favorites"][0], conflict)
        self.assertEqual(len(self.data.documents[1]["favorites"]), 2)

    def test_first_import_for_account_without_user_data(self):
        share_id = self.send(recipient="eve").json()["share_id"]
        result = self.call("POST", f"/{share_id}/import", user="eve", json={"destination": "favorites"})
        self.assertEqual(result.json()["added_count"], 1)
        self.assertEqual(self.data.documents[-1]["_id"], "eve")

    def test_pagination_and_url_sanitization(self):
        for _ in range(22):
            self.send()
        first = self.call("GET", user="bob").json()
        second = self.call("GET", "?offset=20", user="bob").json()
        self.assertTrue(first["has_more"])
        self.assertFalse(second["has_more"])
        self.assertEqual(len({s["id"] for s in first["shares"] + second["shares"]}), 22)
        self.assertEqual(self.call("GET", "?offset=-1", user="bob").status_code, 422)
        self.assertEqual(self.routes._snapshot_tracks([{"name": "Unsafe", "previewUrl": "javascript:alert(1)"}]), [])
        snapshot = self.routes._snapshot_tracks([{"name": "External", "previewUrl": "https://example.com/audio.mp3", "coverUrl": "javascript:alert(1)"}])
        self.assertEqual(snapshot[0]["coverUrl"], "")


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn
        uvicorn.run(fixture()[0], host="127.0.0.1", port=8765)
    else:
        unittest.main()
