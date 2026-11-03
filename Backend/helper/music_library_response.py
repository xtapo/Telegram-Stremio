"""Reuse the serialized music catalog instead of encoding it on every request."""

import asyncio
import gzip
import hashlib
import json

from fastapi import Request, Response


class MusicLibraryResponseCache:
    def __init__(self):
        self._albums = None
        self._snapshot = None
        self._generation = 0
        self._lock = asyncio.Lock()

    def invalidate(self):
        # Saves may update the existing list in place, so identity alone is insufficient.
        self._generation += 1
        self._albums = None
        self._snapshot = None

    @staticmethod
    def _encode(albums):
        body = json.dumps(
            {"status": "success", "source": "database", "albums": albums or []},
            ensure_ascii=False, allow_nan=False, separators=(",", ":"),
        ).encode("utf-8")
        compressed = gzip.compress(body, compresslevel=6, mtime=0)
        digests = hashlib.sha256(body).hexdigest(), hashlib.sha256(compressed).hexdigest()
        return body, compressed, digests

    async def _get_snapshot(self, albums):
        if self._albums is albums and self._snapshot is not None:
            return self._snapshot
        async with self._lock:
            if self._albums is albums and self._snapshot is not None:
                return self._snapshot
            generation = self._generation
            # JSON/gzip must not block playback, heartbeats, or concurrent page requests.
            snapshot = await asyncio.to_thread(self._encode, albums)
            if generation == self._generation:
                self._albums = albums
                self._snapshot = snapshot
            return snapshot

    @staticmethod
    def _accepts_gzip(header):
        qualities = {}
        for part in header.lower().split(","):
            coding, *parameters = part.strip().split(";")
            quality = 1.0
            for parameter in parameters:
                key, _, value = parameter.strip().partition("=")
                if key == "q":
                    try:
                        quality = float(value)
                    except ValueError:
                        quality = 0.0
            qualities[coding] = quality
        return qualities.get("gzip", qualities.get("*", 0.0)) > 0

    async def get_response(self, request: Request, albums: list) -> Response:
        body, compressed, digests = await self._get_snapshot(albums)
        use_gzip = self._accepts_gzip(request.headers.get("accept-encoding", ""))
        encoding = "gzip" if use_gzip else "identity"
        etag = f'"{digests[1 if use_gzip else 0]}-{encoding}"'
        headers = {
            "Cache-Control": "private, no-cache, must-revalidate",
            "Vary": "Accept-Encoding",
            "ETag": etag,
            # Also stops the global GZipMiddleware from compressing the cached response again.
            "Content-Encoding": encoding,
        }
        validators = request.headers.get("if-none-match", "").split(",")
        if any(value.strip().removeprefix("W/") in (etag, "*") for value in validators):
            return Response(status_code=304, headers=headers)
        return Response(
            content=compressed if use_gzip else body,
            media_type="application/json", headers=headers,
        )


music_library_response_cache = MusicLibraryResponseCache()
