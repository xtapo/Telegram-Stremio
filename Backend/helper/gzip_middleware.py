"""Selective GZip ASGI middleware that never compresses media/range/SSE streams.

Starlette <1.0 (including 0.46.2 locked in uv.lock) compresses 206 Partial Content
and audio/* / video/* StreamingResponse bodies whenever an upstream proxy such as
Cloudflare forwards ``Accept-Encoding: gzip`` to the origin. That strips
``Content-Length``, adds ``Content-Encoding: gzip`` onto partial byte-range audio
responses, and triggers ``net::ERR_CONTENT_DECODING_FAILED`` in browsers.
"""

from __future__ import annotations

import asyncio
import zlib
from typing import Iterable, Tuple

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

DEFAULT_EXCLUDED_CONTENT_TYPES: Tuple[str, ...] = (
    "application/gzip",
    "application/octet-stream",
    "application/pdf",
    "application/x-7z-compressed",
    "application/x-gzip",
    "application/x-rar-compressed",
    "application/zip",
    "audio/*",
    "font/woff",
    "font/woff2",
    "image/avif",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/event-stream",
    "video/*",
)

DEFAULT_EXCLUDED_PATH_PREFIXES: Tuple[str, ...] = (
    "/api/music/stream/",
    "/api/music/cover/",
    "/api/system/speedtest/stream",
    "/dl/",
    "/thumb/",
)


def _normalize_content_types(content_types: Iterable[str]) -> Tuple[str, ...]:
    return tuple(ct.partition(";")[0].strip().lower() for ct in content_types if ct)


def accepts_gzip(header: str) -> bool:
    """Parse RFC 9110 Accept-Encoding q-values and return True only if gzip is allowed."""
    if not header:
        return False
    qualities: dict[str, float] = {}
    for part in header.lower().split(","):
        coding, *parameters = part.strip().split(";")
        coding = coding.strip()
        if not coding:
            continue
        quality = 1.0
        for parameter in parameters:
            key, sep, value = parameter.strip().partition("=")
            if sep and key.strip() == "q":
                try:
                    quality = float(value.strip())
                except ValueError:
                    quality = 0.0
        qualities[coding] = quality
    return qualities.get("gzip", qualities.get("*", 0.0)) > 0.0


def _has_no_transform(cache_control: str) -> bool:
    if not cache_control:
        return False
    return any(
        directive.strip().lower() == "no-transform"
        for directive in cache_control.split(",")
    )


def _is_excluded_content_type(content_type: str, excluded: Tuple[str, ...]) -> bool:
    media_type = (content_type or "").partition(";")[0].strip().lower()
    if not media_type:
        return False
    wildcard = media_type.partition("/")[0] + "/*"
    return media_type in excluded or wildcard in excluded


class _SelectiveGZipResponder:
    def __init__(
        self,
        app: ASGIApp,
        *,
        minimum_size: int,
        compresslevel: int,
        thread_minimum_size: int,
        exclude_content_types: Tuple[str, ...],
        can_compress: bool,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self.thread_minimum_size = thread_minimum_size
        self.exclude_content_types = exclude_content_types
        self.can_compress = can_compress

        self._send: Send | None = None
        self._initial_message: Message = {}
        self._started = False
        self._bypass = False
        self._compressor: zlib._Compress | None = None

    @property
    def compressor(self) -> zlib._Compress:
        if self._compressor is None:
            self._compressor = zlib.compressobj(
                self.compresslevel, zlib.DEFLATED, 16 + zlib.MAX_WBITS
            )
        return self._compressor

    def _compress_sync(self, body: bytes, more_body: bool) -> bytes:
        if more_body:
            return self.compressor.compress(body) + self.compressor.flush(zlib.Z_SYNC_FLUSH)
        return self.compressor.compress(body) + self.compressor.flush()

    async def _compress(self, body: bytes, *, more_body: bool) -> bytes:
        if len(body) >= self.thread_minimum_size:
            return await asyncio.to_thread(self._compress_sync, body, more_body)
        return self._compress_sync(body, more_body)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        self._send = send
        await self.app(scope, receive, self.send_with_compression)

    async def send_with_compression(self, message: Message) -> None:
        assert self._send is not None
        message_type = message["type"]

        if message_type == "http.response.start":
            status = int(message.get("status", 200))
            headers = Headers(raw=message.get("headers", []))
            excluded = (
                status < 200
                or status in (204, 206, 304)
                or "content-encoding" in headers
                or "content-range" in headers
                or _has_no_transform(headers.get("cache-control", ""))
                or _is_excluded_content_type(
                    headers.get("content-type", ""), self.exclude_content_types
                )
            )
            if excluded:
                self._bypass = True
                self._started = True
                await self._send(message)
                return

            self._initial_message = message
            return

        if self._bypass:
            await self._send(message)
            return

        if message_type == "http.response.pathsend":
            self._bypass = True
            self._started = True
            if self._initial_message:
                await self._send(self._initial_message)
            await self._send(message)
            return

        if message_type != "http.response.body":
            await self._send(message)
            return

        body = message.get("body", b"")
        more_body = bool(message.get("more_body", False))

        if not self._started:
            self._started = True

            if not more_body and len(body) < self.minimum_size:
                await self._send(self._initial_message)
                await self._send(message)
                return

            headers = MutableHeaders(raw=self._initial_message["headers"])
            headers.add_vary_header("Accept-Encoding")

            if not self.can_compress:
                self._bypass = True
                await self._send(self._initial_message)
                await self._send(message)
                return

            compressed = await self._compress(body, more_body=more_body)
            headers["Content-Encoding"] = "gzip"
            if more_body:
                del headers["Content-Length"]
            else:
                headers["Content-Length"] = str(len(compressed))
            message["body"] = compressed

            await self._send(self._initial_message)
            await self._send(message)
            return

        message["body"] = await self._compress(body, more_body=more_body)
        await self._send(message)


class SelectiveGZipMiddleware:
    """ASGI GZip middleware that skips media streams, byte ranges, and binary payloads."""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compresslevel: int = 6,
        thread_minimum_size: int = 128 * 1024,
        *,
        exclude_content_types: Iterable[str] = DEFAULT_EXCLUDED_CONTENT_TYPES,
        exclude_path_prefixes: Iterable[str] = DEFAULT_EXCLUDED_PATH_PREFIXES,
    ) -> None:
        self.app = app
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel
        self.thread_minimum_size = thread_minimum_size
        self.exclude_content_types = _normalize_content_types(exclude_content_types)
        self.exclude_path_prefixes = tuple(exclude_path_prefixes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = (scope.get("method") or "GET").upper()
        path = scope.get("path") or ""
        headers = Headers(scope=scope)

        if (
            method == "HEAD"
            or "range" in headers
            or path.startswith(self.exclude_path_prefixes)
        ):
            await self.app(scope, receive, send)
            return

        responder = _SelectiveGZipResponder(
            self.app,
            minimum_size=self.minimum_size,
            compresslevel=self.compresslevel,
            thread_minimum_size=self.thread_minimum_size,
            exclude_content_types=self.exclude_content_types,
            can_compress=accepts_gzip(headers.get("accept-encoding", "")),
        )
        await responder(scope, receive, send)
