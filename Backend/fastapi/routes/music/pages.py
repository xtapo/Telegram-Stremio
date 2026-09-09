import asyncio
import gzip
import hashlib
import json
import math
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import time
import unicodedata
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote
import httpx

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.responses import Response as PlainResponse
from fastapi.responses import StreamingResponse

from Backend import db
from pyrogram.errors import AuthBytesInvalid, FloodWait
from Backend.helper.custom_dl import ByteStreamer, get_client_dc_lock
from Backend.helper.music_cache import (
    BLOCK_SIZE as AUDIO_CACHE_BLOCK_SIZE,
    PLAYBACK_WINDOW_TTL,
    smart_audio_cache,
)
from Backend.helper.metadata.music_pipeline import (
    metadata_confidence,
    music_metadata_pipeline,
    normalize_metadata_source,
)
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, Userbot, USERBOT_CLIENT_INDEX, multi_clients, work_loads, client_dc_map, client_failures
from Backend.fastapi.routes.stream_routes import select_best_client, _get_streamer, parse_range_header, _resolve_filename_mime, _build_stream_headers, get_parallel_prefetch
from Backend.fastapi.security.credentials import get_current_user, require_auth
from Backend.fastapi.routes.template_routes import _base_context, templates

from Backend.fastapi.routes.music.common import MUSIC_DIR

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ── 1. Giao diện Quản trị Backend Music Management (/music/manage) ──────────
@router.get("/music/manage", response_class=HTMLResponse)
async def music_management_page(request: Request, _: bool = Depends(require_auth)):
    ctx = _base_context(request)
    ctx["current_user"] = get_current_user(request)
    return templates.TemplateResponse("music_management.html", ctx)


# ── 2. Giao diện Web Music Player & Static Files Fallback ─────────────────────
_MUSIC_HTML_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


@router.get("/music", response_class=HTMLResponse)
@router.get("/music/", response_class=HTMLResponse)
async def get_music_player(request: Request):
    tv_param = request.query_params.get("tv") == "1" or request.query_params.get("mode") == "tv" or request.query_params.get("lite") == "1"
    ua = (request.headers.get("user-agent") or "").lower()
    is_tv_ua = any(k in ua for k in ["androidtv", "smarttv", "bravia", "googletv", "mitv", "aftt", "aftm", "shield", "crkey", "telegrammusictv", "leanback"])

    tv_path = os.path.join(MUSIC_DIR, "tv.html")
    index_path = os.path.join(MUSIC_DIR, "index.html")

    if (tv_param or is_tv_ua) and os.path.exists(tv_path):
        return FileResponse(tv_path, headers=_MUSIC_HTML_CACHE_HEADERS)

    if os.path.exists(index_path):
        return FileResponse(index_path, headers=_MUSIC_HTML_CACHE_HEADERS)
    return HTMLResponse("<h3>Music Player template not found in /Music/index.html</h3>", status_code=404)


@router.get("/tv", response_class=HTMLResponse)
@router.get("/tv/", response_class=HTMLResponse)
@router.get("/tv.html", response_class=HTMLResponse)
@router.get("/music/tv", response_class=HTMLResponse)
@router.get("/music/tv/", response_class=HTMLResponse)
@router.get("/music/tv.html", response_class=HTMLResponse)
@router.get("/music/lite", response_class=HTMLResponse)
@router.get("/Music/tv", response_class=HTMLResponse)
@router.get("/Music/tv/", response_class=HTMLResponse)
@router.get("/Music/tv.html", response_class=HTMLResponse)
@router.get("/Music/lite", response_class=HTMLResponse)
async def get_music_tv_player():
    tv_path = os.path.join(MUSIC_DIR, "tv.html")
    if os.path.exists(tv_path):
        return FileResponse(tv_path, headers=_MUSIC_HTML_CACHE_HEADERS)
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers=_MUSIC_HTML_CACHE_HEADERS)
    return HTMLResponse("<h3>TV Lite template not found</h3>", status_code=404)


@router.get("/music/{filename:path}")
async def get_music_static_file(filename: str):
    """
    Phục vụ trực tiếp CSS, JS, Fonts, Images khi người dùng truy cập /music/style.css, /music/app.js, v.v.
    Bảo đảm 100% không bị lỗi 404 trên Linux / Hugging Face.
    """
    if not filename or filename.strip("/") in ["", "index.html"]:
        return FileResponse(os.path.join(MUSIC_DIR, "index.html"), headers=_MUSIC_HTML_CACHE_HEADERS)

    if filename.strip("/") in ["tv", "tv.html", "lite"]:
        tv_path = os.path.join(MUSIC_DIR, "tv.html")
        if os.path.exists(tv_path):
            return FileResponse(tv_path, headers=_MUSIC_HTML_CACHE_HEADERS)

    clean_name = filename.lstrip("/")
    file_path = os.path.join(MUSIC_DIR, clean_name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"]:
            headers = {"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"}
        else:
            headers = {"Cache-Control": "public, max-age=3600"}
        return FileResponse(file_path, media_type=mime_type, headers=headers)

    # Fallback to index.html if not a static file
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers=_MUSIC_HTML_CACHE_HEADERS)
    return HTMLResponse("File not found", status_code=404)


