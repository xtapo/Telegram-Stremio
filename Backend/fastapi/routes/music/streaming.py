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

from Backend.fastapi.routes.music.common import (
    AUDIO_CACHE_DIR, MUSIC_DIR, WARM_CACHE_PREFETCH_BYTES, _COVER_CACHE_TTL,
    _WARM_CACHE_PREFETCH_INFLIGHT, _cover_cache,
)

router = APIRouter(tags=["Music Player & Telegram Storage"])

def _fix_audio_mime(file_name: str, raw_mime: str) -> tuple[str, str]:
    ext = os.path.splitext(file_name)[1].lower() if "." in file_name else ""
    mime_type = raw_mime or ""
    
    if ext == ".flac":
        mime_type = "audio/flac"
    elif ext == ".mp3":
        mime_type = "audio/mpeg"
    elif ext in [".m4a", ".aac"]:
        mime_type = "audio/mp4"
    elif ext in [".ogg", ".oga"]:
        mime_type = "audio/ogg"
    elif ext == ".opus":
        mime_type = "audio/opus"
    elif ext in [".wav", ".wave"]:
        mime_type = "audio/wav"
    elif ext in [".weba", ".webm"]:
        mime_type = "audio/webm"
    elif ext in [".dsf", ".dff"]:
        mime_type = "audio/x-dsd"
    elif ext == ".ape":
        mime_type = "audio/x-ape"
    elif ext == ".wma":
        mime_type = "audio/x-ms-wma"
    elif ext == ".wv":
        mime_type = "audio/x-wavpack"
    elif not mime_type or mime_type == "application/octet-stream" or not mime_type.startswith("audio/"):
        mime_type = "audio/mpeg"
        if not ext:
            file_name = f"{file_name}.mp3"
            
    return file_name, mime_type


async def _file_range_gen(file_path: str, start: int, length: int, chunk_size: int = 128 * 1024):
    try:
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                read_len = min(chunk_size, remaining)
                chunk = f.read(read_len)
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk
                await asyncio.sleep(0)
    except Exception as e:
        LOGGER.warning(f"[MUSIC CACHE] Lỗi đọc file cache {file_path}: {e}")


def _cache_overlap_bytes(block_offset: int, file_size: int, start: int, end: int) -> int:
    block_end = min(int(file_size) - 1, int(block_offset) + AUDIO_CACHE_BLOCK_SIZE - 1)
    overlap_start = max(int(start), int(block_offset))
    overlap_end = min(int(end), block_end)
    return max(0, overlap_end - overlap_start + 1)


def _build_music_cache_callbacks(
    cache_key: str,
    file_size: int,
    file_name: str,
    mime_type: str,
    start: int,
    end: int,
    explicit_favorite: bool = False,
    count_stats: bool = True,
):
    async def chunk_provider(offset: int, _chunk_size: int):
        served = _cache_overlap_bytes(offset, file_size, start, end)
        return smart_audio_cache.read_block(
            cache_key,
            offset,
            file_size,
            served_bytes=served,
            count_stats=count_stats,
        )

    async def chunk_observer(offset: int, data: bytes):
        tier = smart_audio_cache.tier_for(cache_key, explicit_favorite=explicit_favorite)
        stored = smart_audio_cache.write_block(
            cache_key=cache_key,
            offset=offset,
            data=data,
            file_size=file_size,
            file_name=file_name,
            mime_type=mime_type,
            tier=tier,
        )
        if stored and smart_audio_cache.should_schedule_cleanup():
            asyncio.create_task(asyncio.to_thread(smart_audio_cache.cleanup))

    return chunk_provider, chunk_observer


async def _is_music_user_favorite(user_id: str, chat_id: int, msg_id: int) -> bool:
    if not user_id:
        return False
    try:
        doc = await db.dbs["tracking"]["music_user_data"].find_one(
            {"_id": user_id},
            projection={"favorites": 1},
        )
        for fav in (doc or {}).get("favorites", []):
            try:
                fav_chat = int(fav.get("chat_id") if isinstance(fav, dict) else 0)
                fav_msg = int(fav.get("msg_id") if isinstance(fav, dict) else 0)
            except (TypeError, ValueError):
                continue
            if abs(fav_chat) == abs(int(chat_id)) and fav_msg == int(msg_id):
                return True
    except Exception as exc:
        LOGGER.debug("[MUSIC CACHE] Favorite lookup failed for %s: %s", user_id, exc)
    return False


async def _prefetch_warm_track(chat_id: int, msg_id: int, music_user_id: Optional[str] = None) -> None:
    """Cache the first few blocks of an upcoming track without downloading the full file."""
    cache_key = f"{abs(int(chat_id))}_{int(msg_id)}"
    if cache_key in _WARM_CACHE_PREFETCH_INFLIGHT:
        return
    _WARM_CACHE_PREFETCH_INFLIGHT.add(cache_key)
    try:
        tg_client = None
        client_idx = 0

        if music_user_id:
            try:
                from Backend.fastapi.routes.telegram_qr_auth import get_user_tg_client

                personal = await get_user_tg_client(music_user_id)
                if personal and getattr(personal, "is_connected", False):
                    tg_client = personal
                    client_idx = -99
            except Exception:
                pass

        if tg_client is None and botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
            tg_client = botmod.Userbot
            client_idx = USERBOT_CLIENT_INDEX
        elif tg_client is None and multi_clients:
            client_idx = select_best_client(0)
            tg_client = multi_clients.get(client_idx) or StreamBot
        elif tg_client is None:
            tg_client = StreamBot
            client_idx = 0

        if tg_client is None:
            return

        work_loads.setdefault(client_idx, 0)
        client_failures.setdefault(client_idx, 0)
        streamer = _get_streamer(tg_client, client_idx)
        file_id = await streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
        file_size = int(file_id.file_size or 0)
        if file_size <= 0:
            return

        raw_file_name, raw_mime = _resolve_filename_mime(file_id)
        file_name, mime_type = _fix_audio_mime(raw_file_name, raw_mime)
        end = min(file_size, WARM_CACHE_PREFETCH_BYTES) - 1
        if end < 0:
            return

        part_count = math.ceil((end + 1) / AUDIO_CACHE_BLOCK_SIZE)
        chunk_provider, chunk_observer = _build_music_cache_callbacks(
            cache_key=cache_key,
            file_size=file_size,
            file_name=file_name,
            mime_type=mime_type,
            start=0,
            end=end,
            count_stats=False,
        )
        body_gen = await streamer.prefetch_stream(
            file_id=file_id,
            client_index=client_idx,
            offset=0,
            first_part_cut=0,
            last_part_cut=(end % AUDIO_CACHE_BLOCK_SIZE) + 1,
            part_count=part_count,
            chunk_size=AUDIO_CACHE_BLOCK_SIZE,
            prefetch=min(4, max(1, part_count)),
            parallelism=min(2, max(1, part_count)),
            stream_id=secrets.token_hex(8),
            meta={"cache_prefetch": True, "title": f"Warm cache {msg_id}"},
            request=None,
            chat_id=chat_id,
            message_id=msg_id,
            extra_clients=None,
            chunk_provider=chunk_provider,
            chunk_observer=chunk_observer,
        )
        async for _ in body_gen:
            pass
    except Exception as exc:
        LOGGER.debug("[MUSIC CACHE] Warm prefetch failed for %s/%s: %s", chat_id, msg_id, exc)
    finally:
        _WARM_CACHE_PREFETCH_INFLIGHT.discard(cache_key)


@router.post("/api/music/playback/cache-window")
async def update_music_playback_cache_window(payload: dict, request: Request):
    """Mark current track hot and the next two tracks warm."""
    raw_device_id = str(payload.get("device_id") or "").strip()
    session_user = str(request.session.get("music_user_id") or "").strip()
    client_host = request.client.host if request.client else "unknown"
    owner = raw_device_id or session_user or f"anon:{client_host}"

    ordered_keys: List[str] = []
    warm_tracks: List[tuple[int, int]] = []
    for idx, item in enumerate((payload.get("tracks") or [])[:3]):
        try:
            chat_id = int(item.get("chat_id") if isinstance(item, dict) else 0)
            msg_id = int(item.get("msg_id") if isinstance(item, dict) else 0)
        except (TypeError, ValueError):
            continue
        if chat_id and msg_id:
            ordered_keys.append(f"{abs(chat_id)}_{msg_id}")
            if idx > 0:
                warm_tracks.append((chat_id, msg_id))

    tiers = smart_audio_cache.set_playback_window(owner, ordered_keys)
    for warm_chat_id, warm_msg_id in warm_tracks:
        asyncio.create_task(_prefetch_warm_track(warm_chat_id, warm_msg_id, session_user or None))
    if smart_audio_cache.should_schedule_cleanup():
        asyncio.create_task(asyncio.to_thread(smart_audio_cache.cleanup))
    return {
        "status": "success",
        "cached_window": len(ordered_keys),
        "max_window": 3,
        "ttl_seconds": PLAYBACK_WINDOW_TTL,
        "tiers": tiers,
        "warm_prefetch_bytes": WARM_CACHE_PREFETCH_BYTES,
    }


# ── 4. Stream trực tiếp Audio từ Telegram với HTTP Range 206 + Multi-Bot + Local Cache ──────────────────
@router.get("/api/music/stream/{chat_id}/{msg_id}")
@router.head("/api/music/stream/{chat_id}/{msg_id}")
async def stream_music_track(request: Request, chat_id: int, msg_id: int):
    # Kiểm tra trạng thái phê duyệt nếu người dùng có session đăng nhập
    music_user_id = request.session.get("music_user_id")
    if music_user_id:
        try:
            u_check = await db.dbs["tracking"]["music_users"].find_one({"_id": music_user_id})
            if u_check and u_check.get("is_active") is False:
                raise HTTPException(status_code=403, detail="Tài khoản của bạn đang chờ Quản trị viên phê duyệt.")
        except HTTPException:
            raise
        except Exception:
            pass

    cache_key = f"{abs(chat_id)}_{msg_id}"
    if request.query_params.get("playback") == "1":
        owner = str(request.query_params.get("device") or request.session.get("music_user_id") or "direct")
        smart_audio_cache.mark_hot(owner, cache_key)
    smart_audio_cache.mark_play(cache_key)
    dat_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.dat")
    json_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.json")

    # 1. Kiểm tra cache cục bộ (Cache Hit -> Phục vụ tức thì 0ms, không tốn băng thông Telegram)
    if os.path.exists(dat_path) and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as jf:
                cache_meta = json.load(jf)
            cached_size = cache_meta.get("file_size", 0)
            cached_name = cache_meta.get("file_name", f"track_{msg_id}.mp3")
            cached_mime = cache_meta.get("mime_type", "audio/mpeg")
            
            if cached_size > 0 and os.path.getsize(dat_path) == cached_size:
                try:
                    os.utime(dat_path, None)
                except Exception:
                    pass
                range_header = request.headers.get("Range", "")
                start, end = parse_range_header(range_header, cached_size)
                req_length = end - start + 1
                smart_audio_cache.record_legacy_hit(req_length)
                headers, status = _build_stream_headers(cached_mime, cached_name, req_length, range_header, start, end, cached_size)
                if request.method == "HEAD":
                    return PlainResponse(status_code=status, headers=headers)
                return StreamingResponse(_file_range_gen(dat_path, start, req_length), headers=headers, status_code=status, media_type=cached_mime)
        except Exception as e:
            LOGGER.warning(f"[MUSIC CACHE] Đọc cache thất bại ({e}), fallback sang tải Telegram.")

    # 2. Cache Miss: Tìm client Telegram phù hợp (Ưu tiên User Client cá nhân của người dùng đã đăng nhập QR)
    streamer = None
    client_idx = 0
    tg_client = None

    # Kiểm tra xem người dùng hiện tại có phiên Telegram riêng (QR Login) hay không
    music_user_id = request.session.get("music_user_id")
    user_personal_client = None
    if music_user_id:
        try:
            from Backend.fastapi.routes.telegram_qr_auth import get_user_tg_client
            user_personal_client = await get_user_tg_client(music_user_id)
        except Exception as e:
            LOGGER.warning(f"[MUSIC STREAM] Không thể lấy User Client của {music_user_id}: {e}")

    if user_personal_client and getattr(user_personal_client, "is_connected", False):
        tg_client = user_personal_client
        client_idx = -99  # Designated user-specific client index
        streamer = _get_streamer(tg_client, client_idx)
        LOGGER.info(f"[MUSIC STREAM] Sử dụng phiên Telegram cá nhân của user '{music_user_id}' để stream bài #{msg_id} trong {chat_id}")
    elif botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
        tg_client = botmod.Userbot
        client_idx = USERBOT_CLIENT_INDEX
        streamer = _get_streamer(tg_client, client_idx)
    elif multi_clients:
        client_idx = select_best_client(0)
        tg_client = multi_clients.get(client_idx) or StreamBot
        streamer = _get_streamer(tg_client, client_idx)
    else:
        tg_client = StreamBot
        client_idx = 0
        streamer = _get_streamer(tg_client, client_idx)

    if client_idx not in work_loads:
        work_loads[client_idx] = 0
    if client_idx not in client_failures:
        client_failures[client_idx] = 0

    file_id = None
    try:
        file_id = await streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
    except Exception as e:
        if client_idx == -99:
            LOGGER.info(f"[MUSIC STREAM] Tài khoản cá nhân chưa tham gia Channel riêng tư {chat_id}, tự động chuyển sang Bot Server để stream...")
        else:
            LOGGER.warning(f"[MUSIC STREAM] Client {client_idx} failed to get file properties for {chat_id}/{msg_id}: {e}, thử các client khác...")
        
        # Fallback thử lần lượt các client còn lại
        candidates = []
        if user_personal_client and getattr(user_personal_client, "is_connected", False) and tg_client != user_personal_client:
            candidates.append((-99, user_personal_client))
        if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False) and tg_client != botmod.Userbot:
            candidates.append((USERBOT_CLIENT_INDEX, botmod.Userbot))
        if multi_clients:
            for idx, cl in multi_clients.items():
                if cl != tg_client:
                    candidates.append((idx, cl))
        if StreamBot != tg_client:
            candidates.append((0, StreamBot))

        for c_idx, cl in candidates:
            try:
                alt_streamer = _get_streamer(cl, c_idx)
                if c_idx not in work_loads:
                    work_loads[c_idx] = 0
                if c_idx not in client_failures:
                    client_failures[c_idx] = 0
                file_id = await alt_streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
                if file_id:
                    streamer = alt_streamer
                    client_idx = c_idx
                    tg_client = cl
                    break
            except Exception:
                continue

    if not file_id:
        LOGGER.error(f"[MUSIC STREAM] Message {msg_id} in {chat_id} not accessible by any Telegram client")
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
    explicit_favorite = await _is_music_user_favorite(music_user_id, chat_id, msg_id) if music_user_id else False
    if explicit_favorite:
        smart_audio_cache.hint_favorite(cache_key)

    # Tính toán số lượng worker song song và prefetch an toàn
    token_count = len(multi_clients) - 1 if multi_clients else 0
    parallelism, prefetch_count = get_parallel_prefetch(token_count)
    parallelism = max(1, parallelism)
    prefetch_count = max(4, prefetch_count)

    extra_clients_for_stream = []
    if len(multi_clients) > 1:
        other_indices = sorted(
            (i for i in multi_clients if i != client_idx),
            key=lambda i: (client_failures.get(i, 0), work_loads.get(i, 0)),
        )

        async def _get_extra_file_id(ec_idx: int):
            ec_client = multi_clients[ec_idx]
            ec_streamer = _get_streamer(ec_client, ec_idx)
            try:
                ec_fid = await ec_streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
                return (ec_idx, ec_streamer, ec_fid)
            except Exception as e:
                LOGGER.warning("Extra client %s file_id fetch failed: %s", ec_idx, e)
                return None

        # Keep at least one hot standby even when chunk parallelism is 1. This lets
        # ByteStreamer fail over a slow/FloodWait client inside the same HTTP range
        # response instead of forcing the browser to reconnect.
        standby_count = min(len(other_indices), max(1, parallelism))
        results = await asyncio.gather(*[_get_extra_file_id(i) for i in other_indices[:standby_count]])
        extra_clients_for_stream = [r for r in results if r is not None]

    body_gen = None
    last_flood_wait = None
    last_err = None

    # Prepare list of clients to try (primary first, then alternatives)
    candidates_to_stream = [(client_idx, tg_client, streamer)]
    if user_personal_client and getattr(user_personal_client, "is_connected", False) and tg_client != user_personal_client:
        candidates_to_stream.append((-99, user_personal_client, _get_streamer(user_personal_client, -99)))
    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False) and tg_client != botmod.Userbot:
        candidates_to_stream.append((USERBOT_CLIENT_INDEX, botmod.Userbot, _get_streamer(botmod.Userbot, USERBOT_CLIENT_INDEX)))
    if multi_clients:
        for idx, cl in multi_clients.items():
            if cl != tg_client:
                candidates_to_stream.append((idx, cl, _get_streamer(cl, idx)))
    if StreamBot != tg_client:
        candidates_to_stream.append((0, StreamBot, _get_streamer(StreamBot, 0)))

    for c_idx, cl, strm in candidates_to_stream:
        try:
            c_file_id = file_id
            if cl != tg_client:
                try:
                    c_file_id = await strm.get_file_properties(chat_id=chat_id, message_id=msg_id)
                except Exception:
                    continue

            c_raw_file_name, c_raw_mime = _resolve_filename_mime(c_file_id)
            c_file_name, c_mime_type = _fix_audio_mime(c_raw_file_name, c_raw_mime)
            chunk_provider, chunk_observer = _build_music_cache_callbacks(
                cache_key=cache_key,
                file_size=file_size,
                file_name=c_file_name,
                mime_type=c_mime_type,
                start=start,
                end=end,
                explicit_favorite=explicit_favorite,
            )

            body_gen = await strm.prefetch_stream(
                file_id=c_file_id,
                client_index=c_idx,
                offset=offset,
                first_part_cut=first_part_cut,
                last_part_cut=last_part_cut,
                part_count=part_count,
                chunk_size=chunk_size,
                prefetch=prefetch_count,
                stream_id=stream_id,
                meta=meta,
                parallelism=parallelism,
                request=request,
                chat_id=chat_id,
                message_id=msg_id,
                extra_clients=extra_clients_for_stream,
                chunk_provider=chunk_provider,
                chunk_observer=chunk_observer,
            )
            if body_gen:
                file_id = c_file_id
                break
        except FloodWait as e:
            last_flood_wait = e
            LOGGER.warning(f"[MUSIC STREAM] Client {c_idx} bị FloodWait ({e.value}s), thử client khác...")
            continue
        except Exception as e:
            last_err = e
            LOGGER.warning(f"[MUSIC STREAM] Client {c_idx} lỗi stream: {e}, thử client khác...")
            continue

    if not body_gen:
        if last_flood_wait:
            LOGGER.error(f"[MUSIC STREAM] Tất cả clients đều bị FloodWait: {last_flood_wait.value}s")
            return PlainResponse(content=f"Telegram tạm thời giới hạn tải file này. Vui lòng đợi {last_flood_wait.value} giây.", status_code=429)
        LOGGER.error(f"[MUSIC STREAM] Không thể stream bài hát {chat_id}/{msg_id}: {last_err}")
        return PlainResponse(content="Lỗi khi kết nối Telegram để lấy file audio.", status_code=500)

    raw_file_name, raw_mime = _resolve_filename_mime(file_id)
    file_name, mime_type = _fix_audio_mime(raw_file_name, raw_mime)
    headers, status = _build_stream_headers(mime_type, file_name, req_length, range_header, start, end, file_size)

    if request.method == "HEAD":
        return PlainResponse(status_code=status, headers=headers)

    return StreamingResponse(body_gen, headers=headers, status_code=status, media_type=mime_type)


DEFAULT_COVER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="500" height="500">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#1e1e24"/>
      <stop offset="50%" stop-color="#121217"/>
      <stop offset="100%" stop-color="#0a0a0d"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="100%" stop-color="#ec4899"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)"/>
  <circle cx="250" cy="250" r="180" fill="#18181c" stroke="#2a2a32" stroke-width="6"/>
  <circle cx="250" cy="250" r="140" fill="none" stroke="#22222a" stroke-width="3" stroke-dasharray="8 6"/>
  <circle cx="250" cy="250" r="100" fill="none" stroke="#262630" stroke-width="2"/>
  <circle cx="250" cy="250" r="70" fill="url(#accent)"/>
  <circle cx="250" cy="250" r="22" fill="#0f0f12"/>
  <path d="M245 235 v30 l20 -15 z" fill="#ffffff" opacity="0.9"/>
</svg>""".encode("utf-8")


COVERS_DIR = os.path.join(MUSIC_DIR, "covers")
try:
    os.makedirs(COVERS_DIR, exist_ok=True)
except Exception:
    pass

_COVER_SEMAPHORE = asyncio.Semaphore(2)


# ── 5. Lấy Ảnh Cover / Thumbnail từ Telegram Message ──────────────────────────
@router.get("/api/music/cover/{chat_id}/{msg_id}")
async def get_music_cover(chat_id: int, msg_id: int):
    cache_key = f"{chat_id}_{msg_id}"
    local_cover_path = os.path.join(COVERS_DIR, f"{cache_key}.jpg")

    # 1. Kiểm tra cache file ảnh cục bộ trên đĩa (< 1ms)
    if os.path.exists(local_cover_path) and os.path.getsize(local_cover_path) > 0:
        return FileResponse(local_cover_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})

    # 2. Kiểm tra cache RAM
    now = time.time()
    if cache_key in _cover_cache:
        data, mime, exp = _cover_cache[cache_key]
        if now < exp:
            return PlainResponse(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=604800, immutable"})

    # 3. Sử dụng Semaphore giới hạn tối đa 2 tác vụ tải ảnh đồng thời để KHÔNG BAO GIỜ làm nghẽn kết nối MTProto nghe nhạc
    data = None
    try:
        async with _COVER_SEMAPHORE:
            # Kiểm tra lại cache đĩa trong lock đề phòng request khác vừa tải xong
            if os.path.exists(local_cover_path) and os.path.getsize(local_cover_path) > 0:
                return FileResponse(local_cover_path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})

            clients_to_try = []
            active_userbots = botmod.get_all_active_userbots()
            for ub in active_userbots:
                if ub and getattr(ub, "is_connected", False) and ub not in clients_to_try:
                    clients_to_try.append(ub)
            if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False) and botmod.Userbot not in clients_to_try:
                clients_to_try.append(botmod.Userbot)
            if multi_clients:
                for c in multi_clients.values():
                    if c and getattr(c, "is_connected", False) and c not in clients_to_try:
                        clients_to_try.append(c)
            if StreamBot and getattr(StreamBot, "is_connected", False) and StreamBot not in clients_to_try:
                clients_to_try.append(StreamBot)

            for cl in clients_to_try:
                try:
                    async def _fetch_thumb():
                        msg = await cl.get_messages(chat_id, msg_id)
                        if not msg:
                            return None
                        media = getattr(msg, "audio", None) or getattr(msg, "document", None) or getattr(msg, "video", None)
                        thumbs = getattr(media, "thumbs", None) if media else None
                        if thumbs and len(thumbs) > 0:
                            dc_lock = get_client_dc_lock(cl)
                            async with dc_lock:
                                buf = await cl.download_media(thumbs[-1], in_memory=True)
                            if buf and hasattr(buf, "getvalue"):
                                return buf.getvalue()
                        return None

                    # Timeout tối đa 3.5s để giải phóng connection ngay nếu Telegram phản hồi chậm
                    data = await asyncio.wait_for(_fetch_thumb(), timeout=3.5)
                    if data and len(data) > 0:
                        try:
                            loop = asyncio.get_running_loop()
                            await loop.run_in_executor(None, lambda: open(local_cover_path, "wb").write(data))
                        except Exception:
                            pass
                        break
                except AuthBytesInvalid:
                    LOGGER.debug(f"[COVER] Client {getattr(cl, 'name', 'client')} gặp AuthBytesInvalid cho {chat_id}/{msg_id}, thử client khác...")
                    continue
                except Exception:
                    continue
    except Exception:
        pass

    if data:
        _cover_cache[cache_key] = (data, "image/jpeg", now + _COVER_CACHE_TTL)
        return PlainResponse(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})

    # Nếu không có thumbnail hoặc tải lỗi, cache SVG mặc định trong 24h để không spam Telegram
    _cover_cache[cache_key] = (DEFAULT_COVER_SVG, "image/svg+xml", now + 86400)
    return PlainResponse(content=DEFAULT_COVER_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


