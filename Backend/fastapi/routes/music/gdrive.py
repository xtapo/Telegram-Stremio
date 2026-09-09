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

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ==============================================================================
# 10. GOOGLE DRIVE MUSIC UPLOADER (USER SESSION & BOT)
# ==============================================================================

@router.get("/api/music/uploader/client-status")
async def get_uploader_client_status(_: bool = Depends(require_auth)):
    """Kiểm tra trạng thái các User Sessions và Telegram Bot Client phục vụ upload tốc độ cao"""
    from Backend.helper.session_auth import get_multi_session_status
    multi_status = await get_multi_session_status()
    userbot_connected = bool(botmod.Userbot and getattr(botmod.Userbot, "is_connected", False)) or multi_status["active_sessions"] > 0
    stored_session_exists = multi_status["total_sessions"] > 0
    bot_connected = bool(getattr(StreamBot, "is_connected", False))

    return JSONResponse(content={
        "status": "success",
        "userbot_connected": userbot_connected,
        "stored_session_exists": stored_session_exists,
        "active_userbot_count": multi_status["active_sessions"],
        "total_userbot_count": multi_status["total_sessions"],
        "multi_sessions": multi_status["sessions"],
        "bot_connected": bot_connected,
        "active_mode": "user_session" if userbot_connected or stored_session_exists else "bot",
        "speed_tier": f"⚡ Tối đa ({multi_status['active_sessions']} User Sessions hoạt động)" if userbot_connected else "🤖 Tiêu chuẩn (Telegram Bot API)"
    })


@router.post("/api/music/gdrive-upload/start")
async def start_gdrive_upload(payload: dict, _: bool = Depends(require_auth)):
    """Khởi chạy tiến trình tải nhạc từ Google Drive và upload lên kênh Telegram"""
    url = payload.get("url", "").strip()
    channel_id = payload.get("channel_id", "").strip()
    default_artist = payload.get("default_artist", "").strip()
    default_album = payload.get("default_album", "").strip()
    auto_scrape = payload.get("auto_scrape", True)
    send_as_document = payload.get("send_as_document", False)

    if not url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng nhập URL Google Drive hoặc link tải."})
    if not channel_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng chọn Kênh Telegram đích."})

    import importlib
    import Backend.helper.gdrive_uploader as gdu
    try:
        importlib.reload(gdu)
    except Exception:
        pass
    gdrive_upload_manager = gdu.gdrive_upload_manager
    res = await gdrive_upload_manager.start(
        url=url,
        target_channel_id=channel_id,
        default_artist=default_artist,
        default_album=default_album,
        auto_scrape=auto_scrape,
        send_as_document=send_as_document
    )

    if not res.get("ok"):
        return JSONResponse(status_code=409, content={"status": "error", "message": res.get("message")})

    return JSONResponse(content={
        "status": "success",
        "message": res.get("message"),
        "client_type": res.get("client_type"),
        "data": gdrive_upload_manager.get_status()
    })


@router.get("/api/music/gdrive-upload/status")
async def get_gdrive_upload_status():
    """Lấy trạng thái và tiến trình upload thời gian thực"""
    from Backend.helper.gdrive_uploader import gdrive_upload_manager
    return JSONResponse(content={
        "status": "success",
        "data": gdrive_upload_manager.get_status()
    })


@router.post("/api/music/gdrive-upload/cancel")
async def cancel_gdrive_upload(_: bool = Depends(require_auth)):
    """Hủy tiến trình upload từ Google Drive"""
    from Backend.helper.gdrive_uploader import gdrive_upload_manager
    res = await gdrive_upload_manager.cancel()
    return JSONResponse(content={
        "status": "success" if res.get("ok") else "error",
        "message": res.get("message")
    })


