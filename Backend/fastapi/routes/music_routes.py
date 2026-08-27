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
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, multi_clients, work_loads, client_dc_map, client_failures
from Backend.fastapi.routes.stream_routes import select_best_client, _get_streamer, parse_range_header, _resolve_filename_mime, _build_stream_headers
from Backend.fastapi.security.credentials import get_current_user, require_auth
from Backend.fastapi.routes.template_routes import _base_context, templates

router = APIRouter(tags=["Music Player & Telegram Storage"])

MUSIC_DIR = os.path.abspath("Music")
LIBRARY_CACHE_FILE = os.path.join(MUSIC_DIR, "telegram_library.json")

_cover_cache: Dict[str, tuple] = {}
_COVER_CACHE_TTL = 86400

# Color palette presets for dynamic vinyl glow
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
    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
        return botmod.Userbot
    if multi_clients:
        idx = select_best_client(0)
        return multi_clients.get(idx) or StreamBot
    return StreamBot


# ── 1. Giao diện Quản trị Backend Music Management (/music/manage) ──────────
@router.get("/music/manage", response_class=HTMLResponse)
async def music_management_page(request: Request, _: bool = Depends(require_auth)):
    ctx = _base_context(request)
    ctx["current_user"] = get_current_user(request)
    return templates.TemplateResponse("music_management.html", ctx)


# ── 2. Giao diện Web Music Player & Static Files Fallback ─────────────────────
@router.get("/music", response_class=HTMLResponse)
@router.get("/music/", response_class=HTMLResponse)
async def get_music_player(request: Request):
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h3>Music Player template not found in /Music/index.html</h3>", status_code=404)


@router.get("/music/{filename:path}")
async def get_music_static_file(filename: str):
    """
    Phục vụ trực tiếp CSS, JS, Fonts, Images khi người dùng truy cập /music/style.css, /music/app.js, v.v.
    Bảo đảm 100% không bị lỗi 404 trên Linux / Hugging Face.
    """
    if not filename or filename.strip("/") in ["", "index.html"]:
        return FileResponse(os.path.join(MUSIC_DIR, "index.html"))

    clean_name = filename.lstrip("/")
    file_path = os.path.join(MUSIC_DIR, clean_name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        return FileResponse(file_path, media_type=mime_type)

    # Fallback to index.html if not a static file
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("File not found", status_code=404)


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
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Vui lòng cung cấp Chat ID hoặc Username kênh Telegram."}
        )

    limit = min(max(int(payload.get("limit", 100)), 5), 500)
    default_artist = payload.get("default_artist", "").strip()
    default_album = payload.get("default_album", "").strip()
    auto_scrape = payload.get("auto_scrape", True)

    client = _get_active_client()
    if not client:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": "Telegram Bot / Client chưa sẵn sàng hoặc chưa khởi động xong."}
        )

    # Parse chat_id
    chat_target = raw_chat_id
    if isinstance(raw_chat_id, str):
        clean_id = raw_chat_id.strip()
        if clean_id.startswith("-100") or clean_id.lstrip("-").isdigit():
            try:
                chat_target = int(clean_id)
            except ValueError:
                chat_target = clean_id
        else:
            chat_target = clean_id

    LOGGER.info(f"[MUSIC] Bắt đầu quét kênh Telegram: {chat_target} (tối đa {limit} tin nhắn)...")

    found_tracks = []
    resolved_chat_id = None
    chat_title = str(chat_target)

    # Bước 1: Lấy thông tin kênh
    try:
        chat_info = await client.get_chat(chat_target)
        chat_title = getattr(chat_info, "title", None) or getattr(chat_info, "username", None) or str(chat_target)
        resolved_chat_id = chat_info.id
    except Exception as e:
        err_msg = str(e)
        LOGGER.warning(f"[MUSIC] get_chat failed for {chat_target}: {err_msg}")
        # Nếu là ID số nguyên âm, thử dùng trực tiếp
        if isinstance(chat_target, int):
            resolved_chat_id = chat_target
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Không thể tìm thấy kênh Telegram '{chat_target}'. Lỗi: {err_msg}. Vui lòng kiểm tra lại ID/Username hoặc đảm bảo Bot đã tham gia kênh."
                }
            )

    audio_extensions = (".mp3", ".flac", ".m4a", ".wav", ".aac", ".alac", ".ogg", ".opus", ".dsf", ".ape")

    # Bước 2: Thu thập tin nhắn (hỗ trợ cả get_chat_history và batch message fetch)
    messages_to_process = []
    try:
        # Cách 1: Thử get_chat_history
        async for msg in client.get_chat_history(resolved_chat_id, limit=limit):
            if msg:
                messages_to_process.append(msg)
    except Exception as hist_err:
        LOGGER.warning(f"[MUSIC] get_chat_history failed ({hist_err}), thử dò batch messages...")
        # Cách 2: Fallback dò ID tin nhắn
        try:
            # Dò 1 tin nhắn cuối để lấy max_id
            probe_batch = await client.get_messages(resolved_chat_id, list(range(1, 20)))
            valid_ids = [m.id for m in probe_batch if m]
            start_id = max(valid_ids) if valid_ids else 100
            scan_range = list(range(max(1, start_id - limit), start_id + 1))
            
            # Lấy theo batch 50 tin nhắn
            for i in range(0, len(scan_range), 50):
                sub_ids = scan_range[i:i+50]
                batch_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                for m in batch_msgs:
                    if m:
                        messages_to_process.append(m)
        except Exception as batch_err:
            LOGGER.error(f"[MUSIC] Cả 2 phương thức quét đều lỗi: {batch_err}")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Không thể đọc tin nhắn từ kênh: {hist_err}. Hãy đảm bảo Bot được cấp quyền 'Read Messages' / 'Add Admins' trong kênh!"
                }
            )

    # Bước 2.5: Xây dựng bản đồ ngữ cảnh (Context Map) từ tin nhắn lân cận & Media Groups
    from Backend.helper.metadata.music_scraper import extract_context_from_text, fetch_music_metadata, clean_audio_filename, parse_artist_and_title
    
    media_group_context = {}
    nearby_text_context = {}

    for msg in messages_to_process:
        mgid = getattr(msg, "media_group_id", None)
        cap = getattr(msg, "caption", "") or ""
        txt = getattr(msg, "text", "") or ""
        combined_text = (cap + "\n" + txt).strip()

        if combined_text:
            ctx_art, ctx_alb = extract_context_from_text(combined_text)
            if ctx_art or ctx_alb:
                if mgid:
                    media_group_context[mgid] = (ctx_art, ctx_alb, combined_text)
                nearby_text_context[msg.id] = (ctx_art, ctx_alb)

    # Bước 3: Bóc tách file âm thanh kèm nhận diện ngữ cảnh tin nhắn lân cận
    for idx, msg in enumerate(messages_to_process):
        try:
            media = getattr(msg, "audio", None) or getattr(msg, "document", None)
            if not media:
                continue

            file_name = getattr(media, "file_name", "") or ""
            mime_type = getattr(media, "mime_type", "") or ""
            
            is_audio = bool(getattr(msg, "audio", None)) or mime_type.startswith("audio/") or file_name.lower().endswith(audio_extensions)
            if not is_audio:
                continue

            # Tìm kiếm ngữ cảnh từ media_group hoặc tin nhắn tựa đề lân cận
            ctx_artist, ctx_album = "", ""
            mgid = getattr(msg, "media_group_id", None)
            if mgid and mgid in media_group_context:
                ctx_artist, ctx_album, _ = media_group_context[mgid]

            if not ctx_artist and not ctx_album:
                for offset in range(-5, 6):
                    check_idx = idx + offset
                    if 0 <= check_idx < len(messages_to_process):
                        chk_msg = messages_to_process[check_idx]
                        if chk_msg.id in nearby_text_context:
                            ctx_artist, ctx_album = nearby_text_context[chk_msg.id]
                            break

            effective_artist = default_artist or ctx_artist
            effective_album = default_album or ctx_album

            caption_text = getattr(msg, "caption", "") or ""
            raw_title = getattr(msg.audio, "title", None) if getattr(msg, "audio", None) else None
            raw_artist = getattr(msg.audio, "performer", None) if getattr(msg, "audio", None) else None
            raw_album = getattr(msg.audio, "album", None) if getattr(msg, "audio", None) else None

            duration_sec = getattr(msg.audio, "duration", 0) if getattr(msg, "audio", None) else 0
            file_size_bytes = getattr(media, "file_size", 0) or 0

            # Đoán format & bitrate
            ext = os.path.splitext(file_name)[1].lower().replace(".", "").upper()
            if not ext:
                ext = mime_type.split("/")[-1].upper() if "/" in mime_type else "AUDIO"
            
            audio_format = f"{ext} Hi-Res" if ext in ["FLAC", "WAV", "ALAC", "DSF", "APE"] else f"{ext} Master"

            has_cover = bool(getattr(media, "thumbs", None))
            fallback_cover = f"/api/music/cover/{resolved_chat_id}/{msg.id}" if has_cover else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop"

            # Tự động quét siêu dữ liệu chuẩn xác (Apple Music / Deezer API với Context & Strict Validation)
            scraped_meta = None
            if auto_scrape:
                scraped_meta = await fetch_music_metadata(
                    raw_title=raw_title or "",
                    raw_artist=raw_artist or effective_artist or "",
                    raw_album=raw_album or effective_album or "",
                    file_name=file_name or "",
                    caption=caption_text or "",
                    default_artist=effective_artist or "",
                    default_album=effective_album or ""
                )
            
            if scraped_meta:
                title = scraped_meta.get("title") or raw_title or os.path.splitext(file_name)[0] or f"Track {msg.id}"
                artist = scraped_meta.get("artist") or effective_artist or raw_artist or "Unknown Artist"
                album = scraped_meta.get("album") or effective_album or raw_album or chat_title or "Telegram Music Collection"
                cover_url = scraped_meta.get("cover_url") or fallback_cover
                album_year = scraped_meta.get("year", "2026")
                album_publisher = scraped_meta.get("publisher", f"Telegram: {chat_title}")
            else:
                p_artist, p_title, p_album = parse_artist_and_title(raw_title, raw_artist, raw_album, file_name, caption_text)
                title = p_title or os.path.splitext(file_name)[0] or f"Track {msg.id}"
                artist = effective_artist or p_artist or raw_artist or "Unknown Artist"
                album = effective_album or p_album or raw_album or chat_title or "Telegram Music Collection"
                cover_url = fallback_cover
                album_year = "2026"
                album_publisher = f"Telegram: {chat_title}"

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
                "year": album_year,
                "publisher": album_publisher,
                "stream_url": f"/api/music/stream/{resolved_chat_id}/{msg.id}"
            })
        except Exception as parse_err:
            LOGGER.warning(f"[MUSIC] Bỏ qua tin nhắn lỗi {getattr(msg, 'id', 'unknown')}: {parse_err}")
            continue

    if not found_tracks:
        return JSONResponse(content={
            "status": "warning",
            "message": f"Đã quét qua {len(messages_to_process)} tin nhắn nhưng không tìm thấy file nhạc (.mp3, .flac, audio) nào.",
            "albums": []
        })

    # Bước 4: Nhóm các bài hát theo Album chuẩn chỉnh
    albums_dict = {}
    for track in found_tracks:
        album_name = track["album"]
        if album_name not in albums_dict:
            color_preset = GLOW_PRESETS[len(albums_dict) % len(GLOW_PRESETS)]
            albums_dict[album_name] = {
                "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', album_name.lower())[:30]}",
                "title": album_name.upper(),
                "artist": track["artist"].upper(),
                "year": track.get("year") or time.strftime("%Y"),
                "format": track["format"],
                "totalSize": "0 MB",
                "publisher": track.get("publisher") or f"Telegram: {chat_title}",
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
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(album_list, f, ensure_ascii=False, indent=2)
        LOGGER.info(f"[MUSIC] Đã lưu {len(album_list)} albums ({len(found_tracks)} bài hát) vào cache.")
    except Exception as e:
        LOGGER.error(f"[MUSIC] Lỗi ghi cache thư viện: {e}")

    return JSONResponse(content={
        "status": "success",
        "message": f"Đã quét thành công {len(found_tracks)} bài hát, gom thành {len(album_list)} Album!",
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
        media = getattr(msg, "audio", None) or getattr(msg, "document", None)
        thumbs = getattr(media, "thumbs", None) if media else None
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


# ── 6. Xóa Album / Xóa Bài Hát khỏi Thư Viện Cache ───────────────────────────
@router.delete("/api/music/album/{album_id}")
async def delete_music_album(album_id: str, _: bool = Depends(require_auth)):
    if not os.path.exists(LIBRARY_CACHE_FILE):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})
    try:
        with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
            albums = json.load(f)
        new_albums = [a for a in albums if a.get("id") != album_id]
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_albums, f, ensure_ascii=False, indent=2)
        return JSONResponse(content={"status": "success", "message": "Đã xóa album khỏi thư viện"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.delete("/api/music/track/{chat_id}/{msg_id}")
async def delete_music_track(chat_id: int, msg_id: int, _: bool = Depends(require_auth)):
    if not os.path.exists(LIBRARY_CACHE_FILE):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})
    try:
        with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
            albums = json.load(f)
        for a in albums:
            a["tracks"] = [t for t in a.get("tracks", []) if not (int(t.get("chatId", 0)) == int(chat_id) and int(t.get("msgId", 0)) == int(msg_id))]
        # Loại bỏ album nếu không còn bài hát nào
        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, indent=2)
        return JSONResponse(content={"status": "success", "message": "Đã xóa bài hát khỏi danh sách"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── 7. Chỉnh Sửa Thông Tin Bài Hát / Album (Edit Metadata) ───────────────────
@router.post("/api/music/track/edit")
async def edit_music_track(payload: dict, _: bool = Depends(require_auth)):
    if not os.path.exists(LIBRARY_CACHE_FILE):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})

    chat_id = int(payload.get("chat_id", 0))
    msg_id = int(payload.get("msg_id", 0))
    new_title = payload.get("title", "").strip()
    new_artist = payload.get("artist", "").strip()
    new_album = payload.get("album", "").strip()
    new_cover = payload.get("cover_url", "").strip()

    if not chat_id or not msg_id or not new_title:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu thông tin bài hát"})

    try:
        with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
            albums = json.load(f)

        target_track = None
        for a in albums:
            for t in a.get("tracks", []):
                if int(t.get("chatId", 0)) == chat_id and int(t.get("msgId", 0)) == msg_id:
                    target_track = t
                    if new_title: t["name"] = new_title
                    if new_artist: t["artist"] = new_artist
                    if new_cover: t["coverUrl"] = new_cover
                    break
            if target_track:
                break

        if not target_track:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy bài hát"})

        # Chuyển bài hát sang Album mới nếu có đổi tên album
        if new_album:
            for a in albums:
                a["tracks"] = [t for t in a.get("tracks", []) if not (int(t.get("chatId", 0)) == chat_id and int(t.get("msgId", 0)) == msg_id)]

            dest_album = next((a for a in albums if a.get("title", "").upper() == new_album.upper()), None)
            if not dest_album:
                color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                dest_album = {
                    "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', new_album.lower())[:30]}",
                    "title": new_album.upper(),
                    "artist": (new_artist or target_track.get("artist", "Unknown")).upper(),
                    "year": time.strftime("%Y"),
                    "format": target_track.get("format", "FLAC Hi-Res"),
                    "totalSize": target_track.get("size", "0 MB"),
                    "publisher": f"{new_artist or 'Telegram'}",
                    "coverUrl": new_cover or target_track.get("coverUrl", ""),
                    "glowColors": color_preset,
                    "tracks": []
                }
                albums.append(dest_album)

            dest_album["tracks"].append(target_track)

        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]

        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, indent=2)

        return JSONResponse(content={"status": "success", "message": "Đã cập nhật thông tin bài hát", "albums": albums})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/album/edit")
async def edit_music_album(payload: dict, _: bool = Depends(require_auth)):
    if not os.path.exists(LIBRARY_CACHE_FILE):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})

    album_id = payload.get("album_id", "").strip()
    new_title = payload.get("title", "").strip()
    new_artist = payload.get("artist", "").strip()
    new_cover = payload.get("cover_url", "").strip()
    new_year = payload.get("year", "").strip()

    if not album_id or not new_title:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu thông tin album"})

    try:
        with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
            albums = json.load(f)

        target_album = next((a for a in albums if a.get("id") == album_id), None)
        if not target_album:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy album"})

        if new_title: target_album["title"] = new_title.upper()
        if new_artist:
            target_album["artist"] = new_artist.upper()
            for t in target_album.get("tracks", []):
                t["artist"] = new_artist
        if new_cover: target_album["coverUrl"] = new_cover
        if new_year: target_album["year"] = new_year

        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, indent=2)

        return JSONResponse(content={"status": "success", "message": "Đã cập nhật thông tin album", "albums": albums})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── 7b. Sửa Hàng Loạt Nhiều Bài Hát Cùng Lúc (Bulk Edit Tracks) ─────────────
@router.post("/api/music/tracks/bulk-edit")
async def bulk_edit_music_tracks(payload: dict, _: bool = Depends(require_auth)):
    """
    Sửa ca sĩ, album, ảnh bìa cho nhiều bài hát cùng lúc.
    Payload: { tracks: [{chatId, msgId}], artist, album, cover_url }
    """
    if not os.path.exists(LIBRARY_CACHE_FILE):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})

    track_ids = payload.get("tracks", [])
    new_artist = payload.get("artist", "").strip()
    new_album = payload.get("album", "").strip()
    new_cover = payload.get("cover_url", "").strip()

    if not track_ids:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Chưa chọn bài hát nào"})
    if not new_artist and not new_album and not new_cover:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Chưa nhập thông tin cần sửa"})

    # Tạo set lookup nhanh
    id_set = set()
    for tid in track_ids:
        id_set.add((int(tid.get("chatId", 0)), int(tid.get("msgId", 0))))

    try:
        with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
            albums = json.load(f)

        matched_tracks = []
        for a in albums:
            for t in a.get("tracks", []):
                key = (int(t.get("chatId", 0)), int(t.get("msgId", 0)))
                if key in id_set:
                    if new_artist: t["artist"] = new_artist
                    if new_cover: t["coverUrl"] = new_cover
                    matched_tracks.append(t)

        # Nếu đổi album: chuyển các bài hát sang Album mới
        if new_album and matched_tracks:
            # Xóa tracks cũ khỏi tất cả album
            for a in albums:
                a["tracks"] = [t for t in a.get("tracks", [])
                               if (int(t.get("chatId", 0)), int(t.get("msgId", 0))) not in id_set]

            # Tìm hoặc tạo album đích
            dest_album = next((a for a in albums if a.get("title", "").upper() == new_album.upper()), None)
            if not dest_album:
                color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                dest_album = {
                    "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', new_album.lower())[:30]}",
                    "title": new_album.upper(),
                    "artist": (new_artist or matched_tracks[0].get("artist", "Unknown")).upper(),
                    "year": time.strftime("%Y"),
                    "format": matched_tracks[0].get("format", "FLAC Hi-Res"),
                    "totalSize": "",
                    "publisher": f"{new_artist or 'Telegram'}",
                    "coverUrl": new_cover or matched_tracks[0].get("coverUrl", ""),
                    "glowColors": color_preset,
                    "tracks": []
                }
                albums.append(dest_album)

            dest_album["tracks"].extend(matched_tracks)

        # Xóa album rỗng
        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]

        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, indent=2)

        return JSONResponse(content={
            "status": "success",
            "message": f"Đã cập nhật {len(matched_tracks)} bài hát thành công!",
            "count": len(matched_tracks),
            "albums": albums
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── 8. Tìm Kiếm Ảnh Bìa Album Trực Tuyến (Cover Art Search) ──────────────────
@router.get("/api/music/search-covers")
async def search_music_covers(query: str = Query(..., min_length=1), _: bool = Depends(require_auth)):
    """
    Tìm kiếm danh sách ảnh bìa Album HD từ Apple Music / iTunes và Deezer theo tên nghệ sĩ / album / bài hát
    """
    covers = []
    seen_urls = set()
    import httpx
    import urllib.parse

    # 1. Tìm trên Apple Music / iTunes (entity=album và entity=song)
    for entity in ["album", "song"]:
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity={entity}&limit=6"
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        raw_art = item.get("artworkUrl100", "")
                        if not raw_art:
                            continue
                        hd_cover = raw_art.replace("100x100bb.jpg", "1200x1200bb.webp").replace("100x100bb.png", "1200x1200bb.webp")
                        if hd_cover not in seen_urls:
                            seen_urls.add(hd_cover)
                            title = item.get("collectionName") or item.get("trackName") or query
                            artist = item.get("artistName", "")
                            rel_date = item.get("releaseDate", "")
                            year = rel_date[:4] if len(rel_date) >= 4 else ""
                            covers.append({
                                "title": title,
                                "artist": artist,
                                "year": year,
                                "cover_url": hd_cover,
                                "preview_url": raw_art,
                                "source": "Apple Music"
                            })
        except Exception as e:
            LOGGER.warning(f"[COVER SEARCH] iTunes search failed: {e}")

    # 2. Tìm trên Deezer API
    try:
        url = f"https://api.deezer.com/search/album?q={urllib.parse.quote(query)}&limit=4"
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", []):
                    hd_cover = item.get("cover_xl") or item.get("cover_big") or item.get("cover_medium") or ""
                    if hd_cover and hd_cover not in seen_urls:
                        seen_urls.add(hd_cover)
                        artist_obj = item.get("artist", {})
                        rel_date = item.get("release_date", "")
                        year = rel_date[:4] if len(rel_date) >= 4 else ""
                        covers.append({
                            "title": item.get("title", query),
                            "artist": artist_obj.get("name", ""),
                            "year": year,
                            "cover_url": hd_cover,
                            "preview_url": item.get("cover_medium", hd_cover),
                            "source": "Deezer"
                        })
    except Exception as e:
        LOGGER.warning(f"[COVER SEARCH] Deezer search failed: {e}")

    return JSONResponse(content={"status": "success", "count": len(covers), "covers": covers})



