import asyncio
import json
import math
import mimetypes
import os
import re
import secrets
import time
from typing import Dict, List, Optional
from urllib.parse import quote, unquote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.responses import Response as PlainResponse
from fastapi.responses import StreamingResponse

from Backend.helper.custom_dl import ByteStreamer
from Backend.logger import LOGGER
from Backend.pyrofork.bot import StreamBot, Userbot, multi_clients, work_loads, client_dc_map, client_failures
from Backend.fastapi.routes.stream_routes import select_best_client, _get_streamer, parse_range_header, _resolve_filename_mime, _build_stream_headers

router = APIRouter(tags=["Music Player & Telegram Storage"])

MUSIC_DIR = os.path.abspath("Music")
LIBRARY_CACHE_FILE = os.path.join(MUSIC_DIR, "telegram_library.json")

_cover_cache: Dict[str, tuple] = {}
_COVER_CACHE_TTL = 86400

# Color palette generators for dynamic album vibes
GLOW_PRESETS = [
    {"glow1": "radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)", "glow2": "radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)", "glow2": "radial-gradient(circle, #f59e0b 0%, #c2410c 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #38bdf8 0%, #0284c7 60%, transparent 80%)", "glow2": "radial-gradient(circle, #f472b6 0%, #db2777 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #eab308 0%, #a16207 60%, transparent 80%)", "glow2": "radial-gradient(circle, #6366f1 0%, #312e81 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #10b981 0%, #047857 60%, transparent 80%)", "glow2": "radial-gradient(circle, #06b6d4 0%, #0e7490 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #8b5cf6 0%, #6d28d9 60%, transparent 80%)", "glow2": "radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)"},
]


def _format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}" if unit in ["MB", "GB"] else f"{int(size_bytes)} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _get_active_client():
    if multi_clients:
        idx = select_best_client(0)
        return multi_clients[idx]
    if Userbot and getattr(Userbot, "is_connected", False):
        return Userbot
    if getattr(StreamBot, "is_connected", False):
        return StreamBot
    return None


# ── 1. Giao diện Web Music Player ─────────────────────────────────────────────
@router.get("/music", response_class=HTMLResponse)
@router.get("/music/", response_class=HTMLResponse)
async def get_music_player(request: Request):
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h3>Music Player template not found in /Music/index.html</h3>", status_code=404)


# ── 2. Lấy danh sách Albums & Tracks từ Telegram Cache / Database ─────────────
@router.get("/api/music/albums")
async def get_music_albums():
    if os.path.exists(LIBRARY_CACHE_FILE):
        try:
            with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return JSONResponse(content={"status": "success", "source": "telegram", "albums": data})
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to load library cache: {e}")

    return JSONResponse(content={"status": "empty", "source": "none", "albums": []})


# ── 3. Quét Kênh Telegram để tự động cập nhật thư viện nhạc ───────────────────
@router.post("/api/music/scan")
async def scan_telegram_channel(payload: dict):
    """
    Body payload:
    {
        "chat_id": "-100123456789" hoặc "@channel_username",
        "limit": 100
    }
    """
    raw_chat_id = payload.get("chat_id")
    if not raw_chat_id:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp chat_id hoặc username kênh Telegram.")

    limit = int(payload.get("limit", 150))
    client = _get_active_client()
    if not client:
        raise HTTPException(status_code=503, detail="Telegram client chưa sẵn sàng hoặc chưa kết nối.")

    # Parse chat_id
    chat_target = raw_chat_id
    if isinstance(raw_chat_id, str) and (raw_chat_id.startswith("-100") or raw_chat_id.lstrip("-").isdigit()):
        chat_target = int(raw_chat_id)

    LOGGER.info(f"[MUSIC] Bắt đầu quét kênh Telegram: {chat_target} (tối đa {limit} tin nhắn)...")

    found_tracks = []
    try:
        chat_info = await client.get_chat(chat_target)
        chat_title = chat_info.title or str(chat_target)
        resolved_chat_id = chat_info.id
    except Exception as e:
        LOGGER.error(f"[MUSIC] Không thể truy cập kênh Telegram {chat_target}: {e}")
        raise HTTPException(status_code=400, detail=f"Không thể truy cập kênh Telegram: {e}")

    audio_extensions = (".mp3", ".flac", ".m4a", ".wav", ".aac", ".alac", ".ogg", ".opus", ".dsf")

    async for msg in client.get_chat_history(resolved_chat_id, limit=limit):
        media = msg.audio or msg.document
        if not media:
            continue

        file_name = getattr(media, "file_name", "") or ""
        mime_type = getattr(media, "mime_type", "") or ""
        
        is_audio = bool(msg.audio) or mime_type.startswith("audio/") or file_name.lower().endswith(audio_extensions)
        if not is_audio:
            continue

        title = getattr(msg.audio, "title", None) or os.path.splitext(file_name)[0] or f"Track {msg.id}"
        artist = getattr(msg.audio, "performer", None) or "Unknown Artist"
        album = getattr(msg.audio, "album", None) or chat_title or "Telegram Music Collection"
        duration_sec = getattr(msg.audio, "duration", 0) or 0
        file_size_bytes = getattr(media, "file_size", 0) or 0

        # Đoán format & bitrate
        ext = os.path.splitext(file_name)[1].lower().replace(".", "").upper()
        if not ext:
            ext = mime_type.split("/")[-1].upper() if "/" in mime_type else "AUDIO"
        
        audio_format = f"{ext} Hi-Res" if ext in ["FLAC", "WAV", "ALAC", "DSF"] else f"{ext} Master"

        has_cover = bool(getattr(media, "thumbs", None))
        cover_url = f"/api/music/cover/{resolved_chat_id}/{msg.id}" if has_cover else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop"

        found_tracks.append({
            "msg_id": msg.id,
            "chat_id": resolved_chat_id,
            "title": title.strip(),
            "artist": artist.strip(),
            "album": album.strip(),
            "duration": _format_duration(duration_sec),
            "duration_sec": duration_sec,
            "size": _format_size(file_size_bytes),
            "size_bytes": file_size_bytes,
            "format": audio_format,
            "file_name": file_name,
            "cover_url": cover_url,
            "stream_url": f"/api/music/stream/{resolved_chat_id}/{msg.id}"
        })

    if not found_tracks:
        return JSONResponse(content={
            "status": "warning",
            "message": f"Không tìm thấy file nhạc nào trong {limit} tin nhắn gần nhất của kênh.",
            "albums": []
        })

    # Nhóm các bài hát theo Album
    albums_dict = {}
    for track in found_tracks:
        album_name = track["album"]
        if album_name not in albums_dict:
            color_preset = GLOW_PRESETS[len(albums_dict) % len(GLOW_PRESETS)]
            albums_dict[album_name] = {
                "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', album_name.lower())[:30]}",
                "title": album_name.upper(),
                "artist": track["artist"].upper(),
                "year": time.strftime("%Y"),
                "format": track["format"],
                "totalSize": "0 MB",
                "publisher": f"Telegram: {chat_title}",
                "coverUrl": track["cover_url"],
                "glowColors": color_preset,
                "tracks": []
            }
        
        album_obj = albums_dict[album_name]
        track_index = len(album_obj["tracks"]) + 1
        album_obj["tracks"].append({
            "id": track_index,
            "name": track["title"],
            "artist": track["artist"],
            "duration": track["duration"],
            "size": track["size"],
            "previewUrl": track["stream_url"],
            "chatId": track["chat_id"],
            "msgId": track["msg_id"],
            "coverUrl": track["cover_url"]
        })

    # Tính tổng dung lượng cho từng album
    album_list = list(albums_dict.values())
    for alb in album_list:
        total_b = sum(t.get("size_bytes", 0) for t in found_tracks if t["album"].upper() == alb["title"])
        alb["totalSize"] = _format_size(total_b)
        # Lấy ảnh bài hát đầu tiên làm ảnh đại diện nếu có
        for t in alb["tracks"]:
            if "/api/music/cover/" in t.get("coverUrl", ""):
                alb["coverUrl"] = t["coverUrl"]
                break

    # Lưu cache ra file
    try:
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(album_list, f, ensure_ascii=False, indent=2)
        LOGGER.info(f"[MUSIC] Đã lưu {len(album_list)} albums ({len(found_tracks)} bài hát) vào cache.")
    except Exception as e:
        LOGGER.error(f"[MUSIC] Lỗi ghi cache thư viện: {e}")

    return JSONResponse(content={
        "status": "success",
        "message": f"Đã quét thành công {len(found_tracks)} bài hát, gom thành {len(album_list)} albums!",
        "count": len(found_tracks),
        "albums": album_list
    })


# ── 4. Stream trực tiếp Audio từ Telegram với HTTP Range 206 ──────────────────
@router.get("/api/music/stream/{chat_id}/{msg_id}")
@router.head("/api/music/stream/{chat_id}/{msg_id}")
async def stream_music_track(request: Request, chat_id: int, msg_id: int):
    client = _get_active_client()
    if not client:
        raise HTTPException(status_code=503, detail="Telegram client chưa kết nối.")

    index = select_best_client(0)
    tg_client = multi_clients[index] if multi_clients else client
    streamer: ByteStreamer = _get_streamer(tg_client, index)

    try:
        file_id = await streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        LOGGER.error(f"[MUSIC STREAM] Message {msg_id} in {chat_id} not found: {e}")
        raise HTTPException(status_code=404, detail="Track not found in Telegram")

    file_size = file_id.file_size
    range_header = request.headers.get("Range", "")
    start, end = parse_range_header(range_header, file_size)
    req_length = end - start + 1
    chunk_size = 1024 * 1024
    offset = start - (start % chunk_size)
    first_part_cut = start - offset
    last_part_cut = (end % chunk_size) + 1
    part_count = math.ceil(end / chunk_size) - math.floor(offset / chunk_size)
    stream_id = secrets.token_hex(8)

    meta = {
        "request_path": str(request.url.path),
        "client_host": request.client.host if request.client else None,
        "title": f"Music Track {msg_id}",
        "token": "music-player",
    }

    body_gen = await streamer.prefetch_stream(
        file_id=file_id,
        client_index=index,
        offset=offset,
        first_part_cut=first_part_cut,
        last_part_cut=last_part_cut,
        part_count=part_count,
        chunk_size=chunk_size,
        prefetch=3,
        stream_id=stream_id,
        meta=meta,
        parallelism=1,
        request=request,
        chat_id=chat_id,
        message_id=msg_id,
        extra_clients=[],
    )

    file_name, mime_type = _resolve_filename_mime(file_id)
    headers, status = _build_stream_headers(mime_type, file_name, req_length, range_header, start, end, file_size)

    if request.method == "HEAD":
        return PlainResponse(status_code=status, headers=headers)
    return StreamingResponse(body_gen, headers=headers, status_code=status, media_type=mime_type)


# ── 5. Lấy Ảnh Cover / Thumbnail từ Telegram Message ──────────────────────────
@router.get("/api/music/cover/{chat_id}/{msg_id}")
async def get_music_cover(chat_id: int, msg_id: int):
    cache_key = f"{chat_id}_{msg_id}"
    now = time.time()
    if cache_key in _cover_cache:
        data, exp = _cover_cache[cache_key]
        if now < exp:
            return PlainResponse(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    client = _get_active_client()
    if not client:
        raise HTTPException(status_code=503, detail="No Telegram client")

    try:
        msg = await client.get_messages(chat_id, msg_id)
        media = msg.audio or msg.document
        thumbs = getattr(media, "thumbs", None)
        if not thumbs:
            raise HTTPException(status_code=404, detail="No cover available")

        buf = await client.download_media(thumbs[-1].file_id, in_memory=True)
        data = buf.getvalue()
        _cover_cache[cache_key] = (data, now + _COVER_CACHE_TTL)
        return PlainResponse(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.warning(f"[MUSIC COVER] Failed for {chat_id}/{msg_id}: {e}")
        raise HTTPException(status_code=404, detail="Cover not found")
