"""Run: .venv/Scripts/python -m unittest discover -s tests -p test_gzip_middleware.py -v."""

import ast
import importlib.util
import unittest
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location(
    "isolated_gzip_middleware", ROOT / "Backend/helper/gzip_middleware.py"
)
gzip_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gzip_module)
SelectiveGZipMiddleware = gzip_module.SelectiveGZipMiddleware
accepts_gzip = gzip_module.accepts_gzip


def _load_build_stream_headers():
    source = (ROOT / "Backend/fastapi/routes/stream_routes.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    needed = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in (
            "_content_disposition",
            "_build_stream_headers",
        ):
            needed[node.name] = node
    ns = {"quote": quote}
    exec(
        compile(
            ast.Module(
                body=[needed["_content_disposition"], needed["_build_stream_headers"]],
                type_ignores=[],
            ),
            "Backend/fastapi/routes/stream_routes.py",
            "exec",
        ),
        ns,
    )
    return ns["_build_stream_headers"]


_build_stream_headers = _load_build_stream_headers()


class SelectiveGZipMiddlewareTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)

        self.audio_payload = b"fLaC" + (b"\x00\x01\x02\x03" * 1024)

        @app.get("/api/music/stream/{chat_id}/{msg_id}")
        @app.head("/api/music/stream/{chat_id}/{msg_id}")
        async def music_stream(request: Request, chat_id: int, msg_id: int):
            range_header = request.headers.get("Range", "")
            total = len(self.audio_payload)
            if range_header.startswith("bytes="):
                start_s, end_s = range_header[6:].split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else total - 1
            else:
                start, end = 0, total - 1
            chunk = self.audio_payload[start : end + 1]
            headers, status = _build_stream_headers(
                "audio/flac", "test.flac", len(chunk), range_header, start, end, total
            )
            if request.method == "HEAD":
                return Response(status_code=status, headers=headers)

            async def gen():
                mid = len(chunk) // 2
                yield chunk[:mid]
                yield chunk[mid:]

            return StreamingResponse(
                gen(), headers=headers, status_code=status, media_type="audio/flac"
            )

        @app.get("/dl/{token}/{stream_id}/{name}")
        async def video_stream(request: Request, token: str, stream_id: str, name: str):
            payload = b"\x1a\x45\xdf\xa3" + (b"V" * 4096)
            headers, status = _build_stream_headers(
                "video/x-matroska", name, len(payload), request.headers.get("Range", ""), 0, len(payload) - 1, len(payload)
            )

            async def gen():
                yield payload[:2048]
                yield payload[2048:]

            return StreamingResponse(
                gen(), headers=headers, status_code=status, media_type="video/x-matroska"
            )

        @app.get("/other/audio")
        async def other_audio():
            return Response(content=self.audio_payload, media_type="audio/x-ape")

        @app.get("/other/partial")
        async def other_partial():
            data = b"A" * 4096
            return Response(
                content=data,
                status_code=206,
                media_type="text/plain",
                headers={"Content-Range": f"bytes 0-{len(data) - 1}/{len(data) * 2}"},
            )

        @app.get("/other/no-transform")
        async def other_no_transform():
            return Response(
                content=b"X" * 4096,
                media_type="text/plain",
                headers={"Cache-Control": "public, max-age=60, no-transform"},
            )

        @app.get("/api/system/speedtest/stream")
        async def sse_stream():
            async def gen():
                for i in range(40):
                    yield f"data: {{'step': {i}, 'pad': '{'x' * 64}'}}\n\n".encode("utf-8")

            return StreamingResponse(gen(), media_type="text/event-stream")

        @app.get("/api/music/backup/snapshots/backup.json.gz")
        async def gz_snapshot():
            return Response(content=b"\x1f\x8b" + (b"\x00" * 2048), media_type="application/gzip")

        @app.get("/api/json/large")
        async def large_json():
            return JSONResponse({"items": [{"id": i, "label": "Track " * 8} for i in range(50)]})

        @app.get("/api/json/small")
        async def small_json():
            return JSONResponse({"ok": True})

        @app.get("/api/text/stream")
        async def text_stream():
            async def gen():
                yield ("hello streaming world " * 80).encode("utf-8")
                yield ("second chunk payload " * 80).encode("utf-8")

            return StreamingResponse(gen(), media_type="text/plain")

        self.client = self.enterContext(TestClient(app))

    def test_accepts_gzip_q_values(self):
        self.assertTrue(accepts_gzip("gzip, deflate, br"))
        self.assertTrue(accepts_gzip("br, gzip;q=0.8"))
        self.assertTrue(accepts_gzip("*"))
        self.assertFalse(accepts_gzip(""))
        self.assertFalse(accepts_gzip("identity"))
        self.assertFalse(accepts_gzip("identity;q=1, *;q=0"))
        self.assertFalse(accepts_gzip("gzip;q=0"))
        self.assertFalse(accepts_gzip("gzip;q=0, *;q=1"))
        self.assertFalse(accepts_gzip("br"))
        self.assertFalse(accepts_gzip("gzip;q=invalid"))

    def test_music_stream_range_is_never_gzipped_even_when_proxy_sends_gzip(self):
        response = self.client.get(
            "/api/music/stream/-1001658662232/3802?playback=1&device=web_test",
            headers={"Accept-Encoding": "gzip, deflate, br", "Range": "bytes=0-1023"},
        )
        self.assertEqual(response.status_code, 206)
        self.assertNotIn("content-encoding", response.headers)
        self.assertEqual(response.headers["content-length"], "1024")
        self.assertEqual(
            response.headers["content-range"], f"bytes 0-1023/{len(self.audio_payload)}"
        )
        self.assertIn("no-transform", response.headers["cache-control"])
        self.assertEqual(response.content, self.audio_payload[:1024])

    def test_music_stream_full_get_is_never_gzipped(self):
        response = self.client.get(
            "/api/music/stream/-1004421679659/33859?playback=1",
            headers={"Accept-Encoding": "gzip"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("content-encoding", response.headers)
        self.assertEqual(response.headers["content-length"], str(len(self.audio_payload)))
        self.assertIn("no-transform", response.headers["cache-control"])
        self.assertEqual(response.content, self.audio_payload)

    def test_video_stream_and_media_and_partial_and_sse_are_never_gzipped(self):
        for path, extra_headers, expected_status in (
            ("/dl/tok/abc/movie.mkv", {"Range": "bytes=0-4099"}, 206),
            ("/other/audio", {}, 200),
            ("/other/partial", {}, 206),
            ("/other/no-transform", {}, 200),
            ("/api/system/speedtest/stream", {}, 200),
            ("/api/music/backup/snapshots/backup.json.gz", {}, 200),
        ):
            headers = {"Accept-Encoding": "gzip, deflate, br", **extra_headers}
            response = self.client.get(path, headers=headers)
            self.assertEqual(response.status_code, expected_status, path)
            self.assertNotIn("content-encoding", response.headers, path)

    def test_large_json_and_text_streams_still_compress_when_gzip_accepted(self):
        large = self.client.get("/api/json/large", headers={"Accept-Encoding": "gzip, br"})
        self.assertEqual(large.status_code, 200)
        self.assertEqual(large.headers.get("content-encoding"), "gzip")
        self.assertIn("Accept-Encoding", large.headers.get("vary", ""))
        self.assertEqual(len(large.json()["items"]), 50)

        streamed = self.client.get("/api/text/stream", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(streamed.status_code, 200)
        self.assertEqual(streamed.headers.get("content-encoding"), "gzip")
        self.assertIn("hello streaming world", streamed.text)
        self.assertIn("second chunk payload", streamed.text)

    def test_small_json_and_gzip_q0_are_not_compressed(self):
        small = self.client.get("/api/json/small", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(small.status_code, 200)
        self.assertNotIn("content-encoding", small.headers)

        rejected = self.client.get(
            "/api/json/large", headers={"Accept-Encoding": "identity;q=1, *;q=0"}
        )
        self.assertEqual(rejected.status_code, 200)
        self.assertNotIn("content-encoding", rejected.headers)
        self.assertEqual(len(rejected.json()["items"]), 50)


    def test_pre_encoded_response_is_passed_through_without_double_gzip(self):
        app = FastAPI()
        app.add_middleware(SelectiveGZipMiddleware, minimum_size=1000)

        @app.get("/api/precompressed")
        async def precompressed():
            import gzip

            raw = b'{"ok":true,"pad":"' + (b"a" * 2048) + b'"}'
            return Response(
                content=gzip.compress(raw),
                media_type="application/json",
                headers={"Content-Encoding": "gzip", "Vary": "Accept-Encoding"},
            )

        with TestClient(app) as client:
            resp = client.get("/api/precompressed", headers={"Accept-Encoding": "gzip"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.headers.get("content-encoding"), "gzip")
            self.assertTrue(resp.json()["ok"])


if __name__ == "__main__":
    unittest.main()
