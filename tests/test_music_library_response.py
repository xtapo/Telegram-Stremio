"""Run: .venv/Scripts/python -m unittest discover -s tests -p test_music_library_response.py -v.

Exercise the production HTTP handler and save seam without starting Telegram/MongoDB.
Only those definitions are compiled, excluding the modules' unrelated service imports.
"""

import ast
import asyncio
import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "isolated_music_library_response", ROOT / "Backend/helper/music_library_response.py"
)
response_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(response_module)


def load_definition(filename, name, namespace):
    tree = ast.parse((ROOT / filename).read_text(encoding="utf-8"))
    node = next(item for item in tree.body if isinstance(item, ast.AsyncFunctionDef) and item.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), filename, "exec"), namespace)
    return namespace[name]


ALBUMS = [{
    "id": "album-1", "title": "Đêm nhạc", "artist": "Nghệ sĩ", "year": "2026",
    "tracks": [{"name": f"Bài hát {i}", "chatId": "-100", "msgId": i} for i in range(40)],
}]


class MusicLibraryHTTPTests(unittest.TestCase):
    def setUp(self):
        self.cache = response_module.MusicLibraryResponseCache()
        self.albums = copy.deepcopy(ALBUMS)
        self.encoder = self.enterContext(patch.object(self.cache, "_encode", wraps=self.cache._encode))

        async def load():
            return self.albums

        router = APIRouter()
        namespace = {
            "router": router, "Request": Request, "JSONResponse": JSONResponse,
            "_db_load_library": load, "music_library_response_cache": self.cache,
        }
        load_definition("Backend/fastapi/routes/music/playlists.py", "get_music_albums", namespace)
        app = FastAPI()
        app.add_middleware(GZipMiddleware, minimum_size=1000)
        app.include_router(router)
        self.client = self.enterContext(TestClient(app))

    def test_repeated_requests_reuse_serialization_and_return_304(self):
        first = self.client.get("/api/music/albums")
        self.assertEqual(first.json()["albums"], self.albums)
        self.assertEqual(first.headers["content-encoding"], "gzip")
        self.assertEqual(first.headers["vary"], "Accept-Encoding")
        self.assertEqual(self.encoder.call_count, 1)
        self.client.get("/api/music/albums")
        self.assertEqual(self.encoder.call_count, 1)
        for validator in (first.headers["etag"], '"obsolete", W/' + first.headers["etag"], "*"):
            cached = self.client.get("/api/music/albums", headers={"If-None-Match": validator})
            self.assertEqual(cached.status_code, 304)
            self.assertEqual(cached.content, b"")
        self.assertEqual(self.encoder.call_count, 1)

    def test_encoding_negotiation_and_variant_etags(self):
        compressed = self.client.get("/api/music/albums")
        for encoding in ("identity", "gzip;q=0", "gzip;q=0, *;q=1", "br", "gzip;q=invalid"):
            response = self.client.get("/api/music/albums", headers={"Accept-Encoding": encoding})
            self.assertNotEqual(response.headers.get("content-encoding"), "gzip", encoding)
            self.assertEqual(response.json()["albums"], self.albums)
            self.assertNotEqual(response.headers["etag"], compressed.headers["etag"])
        self.assertEqual(self.encoder.call_count, 1)

    def test_replacing_library_changes_payload_and_etag(self):
        first = self.client.get("/api/music/albums")
        self.albums = []
        response = self.client.get("/api/music/albums", headers={"If-None-Match": first.headers["etag"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["albums"], [])
        self.assertNotEqual(first.headers["etag"], response.headers["etag"])

    def test_save_invalidates_in_place_edits_without_disk_or_remote_io(self):
        first = self.client.get("/api/music/albums")
        self.albums[0]["title"] = "Đã chỉnh sửa"
        namespace = {
            "asyncio": asyncio, "_IN_MEMORY_LIBRARY_CACHE": self.albums,
            "music_library_response_cache": self.cache, "_write_library_cache_files": Mock(),
        }
        save = load_definition("Backend/fastapi/routes/music/storage.py", "_db_save_library", namespace)
        modules = {}
        for name, attribute in (("catalog", "invalidate_artists_cache"), ("playlists", "clear_playlist_cache")):
            module = types.ModuleType("Backend.fastapi.routes.music." + name)
            setattr(module, attribute, Mock())
            modules[module.__name__] = module
        with patch.dict(sys.modules, modules):
            asyncio.run(save(self.albums, sync_remote=False))
        response = self.client.get("/api/music/albums", headers={"If-None-Match": first.headers["etag"]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["albums"][0]["title"], "Đã chỉnh sửa")
        self.assertEqual(self.encoder.call_count, 2)


class MusicLibraryConcurrencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_simultaneous_cold_requests_encode_once(self):
        cache = response_module.MusicLibraryResponseCache()
        with patch.object(cache, "_encode", wraps=cache._encode) as encoder:
            snapshots = await asyncio.gather(*(cache._get_snapshot(ALBUMS) for _ in range(8)))
        self.assertEqual(encoder.call_count, 1)
        self.assertTrue(all(value is snapshots[0] for value in snapshots))

    async def test_save_during_encoding_cannot_publish_an_obsolete_cache(self):
        cache = response_module.MusicLibraryResponseCache()
        started, release = asyncio.Event(), asyncio.Event()
        encode = cache._encode

        async def delayed_encode(function, albums):
            snapshot = encode(albums)
            started.set()
            await release.wait()
            return snapshot

        albums = copy.deepcopy(ALBUMS)
        with patch.object(response_module.asyncio, "to_thread", side_effect=delayed_encode):
            pending = asyncio.create_task(cache._get_snapshot(albums))
            await started.wait()
            albums[0]["title"] = "New metadata"
            cache.invalidate()
            release.set()
            old = await pending
        new = await cache._get_snapshot(albums)
        self.assertNotEqual(new[2], old[2])
        self.assertIn(b"New metadata", new[0])


if __name__ == "__main__":
    unittest.main()
