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

from Backend.fastapi.routes.music.common import AUDIO_CACHE_DIR, GLOW_PRESETS
from Backend.fastapi.routes.music.audio import (
    _format_duration, _format_size, _get_active_client, _parse_duration_str,
    _parse_size_str, _safe_float, deduplicate_tracks, detect_audio_quality,
    detect_country_from_track_info, detect_genre_from_track_info, probe_audio_metadata,
)
from Backend.fastapi.routes.music.storage import (
    _db_load_channels, _db_load_library, _db_save_channels, _db_save_library,
    _db_update_channel_progress, generate_album_id,
)

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ── 3. Quản lý Danh Sách Kênh Nhạc (Channel Management) ───────────────────────
@router.get("/api/music/channels")
async def get_music_channels(_: bool = Depends(require_auth)):
    saved = await _db_load_channels()
    client = _get_active_client()
    result = []

    # Gợi ý kênh từ SettingsManager auth_channels nếu chưa lưu kênh nào
    if not saved:
        try:
            from Backend.helper.settings_manager import SettingsManager
            auth_ch = SettingsManager.current().auth_channels or []
            for ch in auth_ch:
                saved.append({
                    "id": str(ch),
                    "name": str(ch),
                    "username": "",
                    "last_scanned_id": 0,
                    "last_scanned_at": "",
                    "total_tracks": 0,
                    "auto_sync": False
                })
        except Exception:
            pass

    for item in saved:
        ch_id = item.get("id") or item.get("chat_id")
        ch_name = item.get("name") or str(ch_id)
        ch_user = item.get("username") or ""
        last_scanned_id = int(item.get("last_scanned_id", 0) or 0)
        last_scanned_at = str(item.get("last_scanned_at", "") or "")
        total_tracks = int(item.get("total_tracks", 0) or 0)
        auto_sync = bool(item.get("auto_sync", False))

        if client:
            try:
                target = int(ch_id) if str(ch_id).lstrip("-").isdigit() else ch_id
                chat = await client.get_chat(target)
                ch_name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or ch_name
                ch_user = getattr(chat, "username", "") or ch_user
            except Exception:
                pass

        result.append({
            "id": str(ch_id),
            "name": ch_name,
            "username": ch_user,
            "last_scanned_id": last_scanned_id,
            "last_scanned_at": last_scanned_at,
            "total_tracks": total_tracks,
            "auto_sync": auto_sync
        })
    return {"status": "success", "channels": result}


@router.post("/api/music/channels")
async def add_music_channel(payload: dict, _: bool = Depends(require_auth)):
    raw_id = payload.get("chat_id") or payload.get("id")
    if not raw_id:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp Chat ID hoặc Username kênh.")

    client = _get_active_client()
    clean_id = str(raw_id).strip()
    target = int(clean_id) if clean_id.lstrip("-").isdigit() else clean_id

    ch_name = str(clean_id)
    ch_user = ""
    resolved_id = clean_id

    if client:
        try:
            chat = await client.get_chat(target)
            ch_name = getattr(chat, "title", None) or getattr(chat, "first_name", None) or ch_name
            ch_user = getattr(chat, "username", "") or ""
            resolved_id = str(chat.id)
        except Exception as e:
            LOGGER.warning(f"[MUSIC] Cannot verify channel {target}: {e}")
            if not isinstance(target, int):
                raise HTTPException(status_code=400, detail=f"Không thể kết nối đến kênh '{target}': {e}")

    saved = await _db_load_channels()
    for item in saved:
        if str(item.get("id")) == str(resolved_id):
            return {"status": "success", "message": "Kênh đã tồn tại trong danh sách.", "channel": item}

    new_ch = {
        "id": str(resolved_id),
        "name": ch_name,
        "username": ch_user,
        "last_scanned_id": 0,
        "last_scanned_at": "",
        "total_tracks": 0,
        "auto_sync": False
    }
    saved.append(new_ch)
    await _db_save_channels(saved)
    return {"status": "success", "message": f"Đã thêm kênh '{ch_name}' thành công!", "channel": new_ch}


@router.delete("/api/music/channels/{chat_id}")
async def delete_music_channel(chat_id: str, _: bool = Depends(require_auth)):
    saved = await _db_load_channels()
    new_list = [c for c in saved if str(c.get("id")) != str(chat_id)]
    await _db_save_channels(new_list)
    return {"status": "success", "message": "Đã xóa kênh khỏi danh sách quản lý."}


@router.post("/api/music/channels/{chat_id}/reset-progress")
async def reset_music_channel_progress(chat_id: str, _: bool = Depends(require_auth)):
    saved = await _db_load_channels()
    found = False
    target_str = str(chat_id).strip()
    for item in saved:
        if str(item.get("id")) == target_str:
            item["last_scanned_id"] = 0
            item["last_scanned_at"] = ""
            found = True
            break
    if found:
        await _db_save_channels(saved)
        return {"status": "success", "message": "Đã đặt lại mốc quét cho kênh về 0."}
    raise HTTPException(status_code=404, detail="Không tìm thấy kênh trong danh sách.")


async def _get_latest_music_channel_message_id(chat_id: str) -> int:
    client = _get_active_client()
    if not client:
        return 0
    target = int(chat_id) if str(chat_id).strip().lstrip("-").isdigit() else str(chat_id).strip()
    try:
        async for message in client.get_chat_history(target, limit=1):
            return int(getattr(message, "id", 0) or 0)
    except Exception as exc:
        LOGGER.warning(f"[MUSIC AUTO SYNC] Không thể đọc tin nhắn mới nhất của kênh {chat_id}: {exc}")
    return 0


@router.post("/api/music/channels/{chat_id}/auto-sync")
async def set_music_channel_auto_sync(chat_id: str, payload: dict, _: bool = Depends(require_auth)):
    enabled = bool(payload.get("enabled", False))
    saved = await _db_load_channels()
    target_str = str(chat_id).strip()
    channel = next((item for item in saved if str(item.get("id")) == target_str), None)
    if not channel:
        raise HTTPException(status_code=404, detail="Không tìm thấy kênh trong danh sách.")

    # Nếu kênh chưa quét lần nào, lấy tin nhắn hiện tại làm mốc. Nhờ đó việc
    # bật auto-sync chỉ nhận nhạc đăng mới, không vô tình quét toàn bộ lịch sử.
    if enabled and int(channel.get("last_scanned_id", 0) or 0) <= 0:
        baseline_id = await _get_latest_music_channel_message_id(target_str)
        if baseline_id > 0:
            channel["last_scanned_id"] = baseline_id
            channel["last_scanned_at"] = time.strftime("%H:%M %d/%m/%Y")

    channel["auto_sync"] = enabled
    await _db_save_channels(saved)
    if not enabled:
        await music_auto_sync_manager.drop_channel(target_str)

    return {
        "status": "success",
        "enabled": enabled,
        "last_scanned_id": int(channel.get("last_scanned_id", 0) or 0),
        "message": "Đã bật tự động đồng bộ." if enabled else "Đã tắt tự động đồng bộ.",
    }


# ── 3.5 Quản lý Playlist (Bị thay thế bởi Playlist Cá Nhân theo User) ─────────
# Các route playlist đã được chuyển sang music_auth.py

# ── 4. Bộ Quét Kênh Bất Đồng Bộ (Background Music Scanner) ────────────────────
class MusicScanManager:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._cancel_requested: bool = False
        self._status: str = "idle"  # idle | running | completed | cancelled | error
        self._current_channel_id: str = ""
        self._current_channel_title: str = ""
        self._channel_index: int = 0
        self._total_channels: int = 0
        self._processed_messages: int = 0
        self._target_messages: int = 0
        self._current_msg_id: int = 0
        self._target_msg_id: int = 0
        self._found_tracks_count: int = 0
        self._duplicates_removed: int = 0
        self._current_track: str = ""
        self._error_message: str = ""
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._logs: list = []

    def get_status(self) -> dict:
        elapsed = 0
        if self._start_time > 0:
            end = self._end_time if self._end_time > 0 else time.time()
            elapsed = int(end - self._start_time)
        return {
            "status": self._status,
            "current_channel_id": str(self._current_channel_id),
            "current_channel_title": self._current_channel_title,
            "channel_index": self._channel_index,
            "total_channels": self._total_channels,
            "processed_messages": self._processed_messages,
            "target_messages": self._target_messages,
            "current_msg_id": self._current_msg_id,
            "target_msg_id": self._target_msg_id,
            "found_tracks_count": self._found_tracks_count,
            "duplicates_removed": self._duplicates_removed,
            "current_track": self._current_track,
            "error_message": self._error_message,
            "elapsed_seconds": elapsed,
            "logs": self._logs[-8:],
        }

    def _log(self, msg: str):
        LOGGER.info(f"[MUSIC SCAN] {msg}")
        self._logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        if len(self._logs) > 50:
            self._logs.pop(0)

    async def start(
        self,
        channels: list,
        limit: int = 100,
        resume: bool = False,
        mode: str = "append",
        auto_scrape: bool = True,
        default_artist: str = "",
        default_album: str = "",
        from_msg_id: int = 0,
        to_msg_id: int = 0,
    ) -> dict:
        if self._status == "running":
            return {"ok": False, "message": "Tiến trình quét nhạc đang chạy."}

        client = _get_active_client()
        if not client:
            return {"ok": False, "message": "Telegram Bot / Client chưa kết nối."}

        self._cancel_requested = False
        self._status = "running"
        self._processed_messages = 0
        self._current_msg_id = 0
        self._target_msg_id = 0
        if from_msg_id > 0 and to_msg_id >= from_msg_id:
            self._target_messages = len(channels) * (to_msg_id - from_msg_id + 1)
        elif limit > 0:
            self._target_messages = len(channels) * limit
        else:
            self._target_messages = 0  # 0 = Không giới hạn

        self._found_tracks_count = 0
        self._duplicates_removed = 0
        self._current_track = ""
        self._error_message = ""
        self._start_time = time.time()
        self._end_time = 0.0
        self._logs = []
        self._channel_index = 0
        self._total_channels = len(channels)

        self._task = asyncio.create_task(
            self._run_scan_loop(
                channels=channels,
                limit=limit,
                resume=resume,
                mode=mode,
                auto_scrape=auto_scrape,
                default_artist=default_artist,
                default_album=default_album,
                from_msg_id=from_msg_id,
                to_msg_id=to_msg_id,
            )
        )
        return {"ok": True, "message": f"Bắt đầu quét {len(channels)} kênh Telegram."}

    async def cancel(self) -> dict:
        if self._status != "running":
            return {"ok": False, "message": "Không có tiến trình quét nào đang chạy."}
        self._cancel_requested = True
        self._status = "cancelled"
        self._end_time = time.time()
        self._log("Người dùng đã hủy tiến trình quét.")
        if self._task and not self._task.done():
            self._task.cancel()
        return {"ok": True, "message": "Đã gửi yêu cầu hủy quét."}

    async def _run_scan_loop(
        self,
        channels: list,
        limit: int,
        resume: bool,
        mode: str,
        auto_scrape: bool,
        default_artist: str,
        default_album: str,
        from_msg_id: int = 0,
        to_msg_id: int = 0,
    ):
        try:
            client = _get_active_client()
            all_scanned_tracks = []
            audio_extensions = (".mp3", ".flac", ".m4a", ".wav", ".aac", ".alac", ".ogg", ".opus", ".dsf", ".ape")
            from Backend.helper.metadata.music_scraper import extract_context_from_text, fetch_music_metadata, clean_audio_filename, parse_artist_and_title, classify_genre_and_country
            from Backend.helper.metadata.audio_fingerprint import recognize_audio_from_telegram

            saved_channels_map = {str(c.get("id")): c for c in await _db_load_channels()}

            for idx, raw_ch in enumerate(channels, 1):
                if self._cancel_requested:
                    break
                self._channel_index = idx
                clean_target = raw_ch
                if isinstance(raw_ch, str):
                    clean_s = raw_ch.strip()
                    if clean_s.startswith("-100") or clean_s.lstrip("-").isdigit():
                        try:
                            clean_target = int(clean_s)
                        except ValueError:
                            clean_target = clean_s
                    else:
                        clean_target = clean_s

                chat_title = str(clean_target)
                resolved_chat_id = clean_target if isinstance(clean_target, int) else None
                try:
                    chat_info = await client.get_chat(clean_target)
                    chat_title = getattr(chat_info, "title", None) or getattr(chat_info, "username", None) or str(clean_target)
                    resolved_chat_id = chat_info.id
                except Exception as e:
                    self._log(f"Không thể get_chat '{clean_target}': {e}")
                    if not isinstance(clean_target, int):
                        continue

                self._current_channel_id = str(resolved_chat_id or clean_target)
                self._current_channel_title = chat_title
                self._log(f"Đang quét kênh [{idx}/{len(channels)}]: {chat_title} ({self._current_channel_id})")

                ch_saved = saved_channels_map.get(self._current_channel_id) or {}
                last_checkpoint_id = int(ch_saved.get("last_scanned_id", 0) or 0)
                highest_seen_id = last_checkpoint_id
                channel_tracks_found = 0
                messages_since_checkpoint = 0

                latest_msg_id = 0
                try:
                    async for m in client.get_chat_history(resolved_chat_id, limit=1):
                        if m and m.id:
                            latest_msg_id = m.id
                            break
                except Exception:
                    pass

                if from_msg_id > 0:
                    scan_from = from_msg_id
                    scan_to = to_msg_id if (to_msg_id > 0 and to_msg_id >= from_msg_id) else (latest_msg_id or (from_msg_id + 500))
                elif resume or limit == -1:
                    if last_checkpoint_id > 0:
                        scan_from = last_checkpoint_id + 1
                        if latest_msg_id > 0 and scan_from > latest_msg_id:
                            self._log(f"Kênh '{chat_title}' đã ở trạng thái mới nhất (đã quét tới ID #{last_checkpoint_id}). Không có bài mới.")
                            continue
                    else:
                        scan_from = 1
                    scan_to = latest_msg_id or (scan_from + 500)
                elif limit == 0:
                    scan_from = 1
                    scan_to = latest_msg_id or 1000
                elif limit > 0:
                    if latest_msg_id > 0:
                        scan_from = max(1, latest_msg_id - limit + 1)
                        scan_to = latest_msg_id
                    else:
                        scan_from = 1
                        scan_to = limit
                else:
                    scan_from = 1
                    scan_to = latest_msg_id or 100

                self._current_msg_id = scan_from
                self._target_msg_id = scan_to
                scan_count = max(0, scan_to - scan_from + 1)
                self._target_messages = scan_count
                self._log(f"Quét dải ID tin nhắn #{scan_from} -> #{scan_to} (Tổng {scan_count} tin nhắn)...")

                try:
                    batch_size = max(10, min(50, int(os.environ.get("MUSIC_SCAN_BATCH_SIZE", "25"))))
                except (TypeError, ValueError):
                    batch_size = 25
                try:
                    scan_track_delay = max(0.0, min(1.0, float(os.environ.get("MUSIC_SCAN_TRACK_DELAY", "0.05"))))
                except (TypeError, ValueError):
                    scan_track_delay = 0.05
                for batch_start in range(scan_from, scan_to + 1, batch_size):
                    if self._cancel_requested:
                        break
                    batch_end = min(scan_to + 1, batch_start + batch_size)
                    sub_ids = list(range(batch_start, batch_end))
                    self._current_msg_id = sub_ids[-1]

                    b_msgs = []
                    try:
                        b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                    except FloodWait as fw:
                        self._log(f"Telegram yêu cầu chờ FloodWait {fw.value}s trong batch — đang tự động tạm dừng...")
                        await asyncio.sleep(fw.value + 1)
                        try:
                            b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                        except Exception:
                            b_msgs = []
                    except Exception as e:
                        self._log(f"Lỗi lấy cụm tin nhắn {sub_ids[0]}-{sub_ids[-1]}: {e}")
                        b_msgs = []

                    valid_msgs = [m for m in b_msgs if m]
                    for m in valid_msgs:
                        if m.id > highest_seen_id:
                            highest_seen_id = m.id

                    media_group_context = {}
                    nearby_text_context = {}
                    for msg in valid_msgs:
                        mgid = getattr(msg, "media_group_id", None)
                        cap = getattr(msg, "caption", "") or ""
                        txt = getattr(msg, "text", "") or ""
                        combined = (cap + "\n" + txt).strip()
                        if combined:
                            c_art, c_alb = extract_context_from_text(combined)
                            if c_art or c_alb:
                                if mgid:
                                    media_group_context[mgid] = (c_art, c_alb, combined)
                                nearby_text_context[msg.id] = (c_art, c_alb)

                    for m_idx, msg in enumerate(valid_msgs):
                        if self._cancel_requested:
                            break
                        try:
                            audio_obj = getattr(msg, "audio", None)
                            doc_obj = getattr(msg, "document", None)
                            media = audio_obj or doc_obj
                            if not media:
                                continue
                            f_name = getattr(media, "file_name", "") or ""
                            m_type = getattr(media, "mime_type", "") or ""
                            file_unique_id = str(getattr(media, "file_unique_id", "") or "")
                            is_audio = bool(audio_obj) or m_type.startswith("audio/") or f_name.lower().endswith(audio_extensions)
                            if not is_audio:
                                continue

                            caption_text = getattr(msg, "caption", "") or ""
                            raw_title = getattr(audio_obj, "title", None) if audio_obj else None
                            raw_artist = getattr(audio_obj, "performer", None) if audio_obj else None
                            raw_album = getattr(audio_obj, "album", None) if audio_obj else None
                            duration_sec = getattr(audio_obj, "duration", 0) if audio_obj else 0
                            duration_for_quality = duration_sec
                            file_size_bytes = getattr(media, "file_size", 0) or 0

                            if not duration_sec and doc_obj:
                                for attr in getattr(doc_obj, "attributes", []) or []:
                                    if hasattr(attr, "duration") and attr.duration:
                                        duration_sec = int(attr.duration)
                                        duration_for_quality = duration_sec
                                    if hasattr(attr, "performer") and attr.performer and not raw_artist:
                                        raw_artist = attr.performer
                                    if hasattr(attr, "title") and attr.title and not raw_title:
                                        raw_title = attr.title

                            if not duration_sec and file_size_bytes > 0:
                                est_kbps = 900 if ("flac" in f_name.lower() or "wav" in f_name.lower()) else 320
                                duration_sec = max(45, int(file_size_bytes / (est_kbps * 125)))

                            audio_probe = {}
                            legacy_cache_key = f"{abs(int(resolved_chat_id))}_{int(msg.id)}"
                            legacy_audio_path = os.path.join(AUDIO_CACHE_DIR, f"{legacy_cache_key}.dat")
                            if os.path.isfile(legacy_audio_path):
                                try:
                                    if not file_size_bytes or os.path.getsize(legacy_audio_path) == file_size_bytes:
                                        audio_probe = await asyncio.to_thread(probe_audio_metadata, legacy_audio_path)
                                except OSError:
                                    audio_probe = {}
                            if audio_probe:
                                probed_duration = _safe_float(audio_probe.get("duration"))
                                if probed_duration > 0:
                                    duration_sec = int(round(probed_duration))
                                    duration_for_quality = duration_sec

                            p_art, p_tit, p_alb = parse_artist_and_title(raw_title, raw_artist, raw_album, f_name, caption_text)

                            ctx_artist, ctx_album = "", ""
                            mgid = getattr(msg, "media_group_id", None)
                            if mgid and mgid in media_group_context:
                                ctx_artist, ctx_album, _ = media_group_context[mgid]
                            
                            if not ctx_artist and not ctx_album and caption_text:
                                ctx_artist, ctx_album = extract_context_from_text(caption_text)

                            if not ctx_artist or not ctx_album:
                                for offset in [-1, -2]:
                                    chk_i = m_idx + offset
                                    if 0 <= chk_i < len(valid_msgs):
                                        chk_m = valid_msgs[chk_i]
                                        msg_date = getattr(msg, "date", None)
                                        chk_date = getattr(chk_m, "date", None)
                                        time_diff = abs((msg_date - chk_date).total_seconds()) if msg_date and chk_date else 0
                                        if time_diff <= 300 and chk_m.id in nearby_text_context:
                                            n_art, n_alb = nearby_text_context[chk_m.id]
                                            if not ctx_artist and n_art: ctx_artist = n_art
                                            if not ctx_album and n_alb: ctx_album = n_alb
                                            break

                            final_artist = default_artist or raw_artist or p_art or ctx_artist or "Unknown Artist"
                            final_album = default_album or raw_album or p_alb or ctx_album or chat_title or "Telegram Music Collection"
                            final_title = p_tit or raw_title or os.path.splitext(f_name)[0] or f"Track {msg.id}"

                            identity_source = "embedded" if raw_title and raw_artist else "filename"
                            identity_confidence = metadata_confidence(identity_source)
                            manual_override = False
                            local_fingerprint = ""
                            cached_year = ""
                            fingerprint_cover = None
                            fingerprint_genre = None

                            # Persistent cache is checked before any network/audio recognition.
                            cached_meta = await music_metadata_pipeline.get_cached(
                                chat_id=resolved_chat_id,
                                msg_id=msg.id,
                                file_unique_id=file_unique_id,
                            )
                            if cached_meta and cached_meta.get("title"):
                                final_title = cached_meta.get("title") or final_title
                                final_artist = cached_meta.get("artist") or final_artist
                                final_album = cached_meta.get("album") or final_album
                                fingerprint_cover = cached_meta.get("cover_url") or None
                                fingerprint_genre = cached_meta.get("genre") or None
                                cached_year = str(cached_meta.get("year") or "")
                                local_fingerprint = str(cached_meta.get("fingerprint") or "")
                                identity_source = normalize_metadata_source(cached_meta.get("source"))
                                identity_confidence = metadata_confidence(
                                    identity_source,
                                    cached_meta.get("confidence"),
                                )
                                manual_override = bool(cached_meta.get("manual_override"))

                            needs_audio_identity = (
                                final_artist == "Unknown Artist"
                                or final_title.lower().startswith("track")
                                or final_title.lower().startswith("audio")
                                or "track" in f_name.lower()
                            )
                            if not cached_meta and needs_audio_identity:
                                fg_res = await recognize_audio_from_telegram(
                                    client=client,
                                    message=msg,
                                    is_manual=False,
                                    chat_id=resolved_chat_id,
                                    msg_id=msg.id,
                                    hint_title=final_title if not final_title.lower().startswith("track") else None,
                                    hint_artist=final_artist if final_artist != "Unknown Artist" else None,
                                    hint_album=final_album if final_album != (chat_title or "Telegram Music Collection") else None
                                )
                                if fg_res:

                                    final_title = fg_res.get("title") or final_title
                                    final_artist = fg_res.get("artist") or final_artist
                                    final_album = fg_res.get("album") or final_album
                                    fingerprint_cover = fg_res.get("cover_url")
                                    fingerprint_genre = fg_res.get("genre")
                                    local_fingerprint = str(fg_res.get("fingerprint") or "")
                                    identity_source = normalize_metadata_source(fg_res.get("source"))
                                    identity_confidence = metadata_confidence(
                                        identity_source,
                                        fg_res.get("confidence"),
                                    )

                            audio_fmt, q_tier, calc_br = detect_audio_quality(
                                file_name=f_name, mime_type=m_type, file_size_bytes=file_size_bytes,
                                duration_sec=duration_for_quality, caption_text=caption_text,
                                probe_data=audio_probe,
                            )
                            has_cover = bool(getattr(media, "thumbs", None))
                            fallback_cover = fingerprint_cover or (f"/api/music/cover/{resolved_chat_id}/{msg.id}" if has_cover else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop")

                            scraped_meta = None
                            if auto_scrape and not cached_meta and not manual_override:
                                scraped_meta = await fetch_music_metadata(
                                    raw_title=final_title,
                                    raw_artist=final_artist,
                                    raw_album=final_album,
                                    file_name=f_name or "",
                                    caption=caption_text or "",
                                    default_artist=default_artist or "",
                                    default_album=default_album or ""
                                )

                            if scraped_meta:
                                online_confidence = metadata_confidence("online")
                                # Dịch vụ online chỉ được thay identity khi bằng chứng hiện tại yếu hơn.
                                # Với embedded/fingerprint/Shazam, online chỉ làm giàu cover/year/genre.
                                if identity_confidence <= online_confidence:
                                    t_title = scraped_meta.get("title") or final_title
                                    t_artist = scraped_meta.get("artist") or final_artist
                                    t_album = scraped_meta.get("album") or final_album
                                    identity_source = normalize_metadata_source(
                                        scraped_meta.get("source") or "online"
                                    )
                                    identity_confidence = metadata_confidence(
                                        identity_source,
                                        scraped_meta.get("confidence"),
                                    )
                                else:
                                    t_title = final_title
                                    t_artist = final_artist
                                    t_album = final_album
                                t_cover = scraped_meta.get("cover_url") or fallback_cover
                                t_year = scraped_meta.get("year", time.strftime("%Y"))
                                t_pub = scraped_meta.get("publisher", f"Telegram: {chat_title}")
                                t_genre = scraped_meta.get("genre") or fingerprint_genre or ""
                                t_country = scraped_meta.get("country") or ""
                                t_era = scraped_meta.get("era") or ""
                            else:
                                t_title = final_title
                                t_artist = final_artist
                                t_album = final_album
                                t_cover = fallback_cover
                                t_year = cached_year or time.strftime("%Y")
                                t_pub = f"Telegram: {chat_title}"
                                t_genre = fingerprint_genre or ""
                                t_country = ""
                                t_era = ""

                            cls_meta = classify_genre_and_country(
                                title=t_title,
                                artist=t_artist,
                                album=t_album,
                                raw_genre=t_genre,
                                file_name=f_name or "",
                                caption=caption_text or "",
                                year=t_year
                            )
                            t_genre = cls_meta["genre"]
                            t_country = t_country or cls_meta["country"]
                            t_era = t_era or cls_meta["era"]

                            self._current_track = f"{t_title} - {t_artist}"
                            all_scanned_tracks.append({
                                "msg_id": msg.id,
                                "chat_id": resolved_chat_id,
                                "title": t_title.strip(),
                                "artist": t_artist.strip(),
                                "album": t_album.strip(),
                                "duration": _format_duration(duration_sec),
                                "duration_sec": duration_sec,
                                "size": _format_size(file_size_bytes),
                                "size_bytes": file_size_bytes,
                                "format": audio_fmt,
                                "qualityTier": q_tier,
                                "bitrate": calc_br,
                                "audioProbe": audio_probe,
                                "file_name": f_name,
                                "file_unique_id": file_unique_id,
                                "fingerprint": local_fingerprint,
                                "metadata_source": identity_source,
                                "metadata_confidence": identity_confidence,
                                "manual_override": manual_override,
                                "isShazam": identity_source == "shazam",
                                "cover_url": t_cover,
                                "year": t_year,
                                "publisher": t_pub,
                                "genre": t_genre,
                                "country": t_country,
                                "era": t_era,
                                "stream_url": f"/api/music/stream/{resolved_chat_id}/{msg.id}"
                            })
                            channel_tracks_found += 1
                            self._found_tracks_count = len(all_scanned_tracks)
                            if scan_track_delay > 0:
                                await asyncio.sleep(scan_track_delay)
                        except Exception:
                            continue

                    # Chỉ persist checkpoint mỗi 500 message (hoặc batch cuối)
                    # để giảm ghi JSON + MongoDB. Trước đây mỗi 50 message ghi
                    # một lần, gây nhiều disk/database I/O khi quét kênh lớn.
                    self._processed_messages += len(sub_ids)
                    messages_since_checkpoint += len(sub_ids)
                    checkpoint_to_save = max(highest_seen_id, sub_ids[-1])
                    is_last_batch = batch_end > scan_to
                    if messages_since_checkpoint >= 500 or is_last_batch:
                        await _db_update_channel_progress(
                            self._current_channel_id,
                            checkpoint_to_save,
                            total_tracks=channel_tracks_found,
                        )
                        messages_since_checkpoint = 0
                    await asyncio.sleep(0.02)

            if self._cancel_requested:
                self._status = "cancelled"
                self._end_time = time.time()
                return

            self._log(f"Quét Telegram hoàn tất! Tìm thấy {len(all_scanned_tracks)} bài. Đang tổng hợp thư viện...")
            self._current_track = "Đang tổng hợp thư viện..."
            finalize_started = time.time()

            existing_tracks = []
            if mode == "append":
                try:
                    old_albums = await _db_load_library()
                    for a in old_albums:
                        for t in a.get("tracks", []):
                            existing_tracks.append({
                                "msg_id": int(t.get("msgId", 0)),
                                "chat_id": int(t.get("chatId", 0)),
                                "title": t.get("name", ""),
                                "artist": t.get("artist", a.get("artist", "")),
                                "album": a.get("title", ""),
                                "duration": t.get("duration", "--:--"),
                                "duration_sec": _parse_duration_str(t.get("duration", "")),
                                "size": t.get("size", "0 B"),
                                "size_bytes": _parse_size_str(t.get("size", "")),
                                "format": t.get("format", a.get("format", "FLAC")),
                                "qualityTier": t.get("qualityTier", a.get("qualityTier", "lossless")),
                                "bitrate": t.get("bitrate", "Lossless"),
                                "audioProbe": t.get("audioProbe") if isinstance(t.get("audioProbe"), dict) else {},
                                "file_name": "",
                                "file_unique_id": t.get("fileUniqueId", ""),
                                "fingerprint": t.get("fingerprint", ""),
                                "metadata_source": t.get("metadataSource", "unknown"),
                                "metadata_confidence": t.get("metadataConfidence", 0.5),
                                "manual_override": bool(t.get("manualOverride", False)),
                                "cover_url": t.get("coverUrl", a.get("coverUrl", "")),
                                "year": a.get("year", "2026"),
                                "publisher": a.get("publisher", ""),
                                "isShazam": bool(t.get("isShazam", False)),
                                "stream_url": t.get("previewUrl", "")
                            })
                except Exception as e:
                    self._log(f"Không thể đọc thư viện cũ: {e}")

            combined_pool = existing_tracks + all_scanned_tracks
            combined_pool, dup_removed = await asyncio.to_thread(deduplicate_tracks, combined_pool)
            self._duplicates_removed = dup_removed

            # Group into Albums + thống kê trong một lượt. Trước đây vòng final
            # lại lọc toàn bộ combined_pool cho từng album (O(album * track)),
            # gây CPU tăng vọt khi thư viện lớn.
            albums_dict = {}
            album_stats = {}
            for tr_idx, tr in enumerate(combined_pool, start=1):
                alb_name = tr["album"]
                if alb_name not in albums_dict:
                    color_preset = GLOW_PRESETS[len(albums_dict) % len(GLOW_PRESETS)]
                    album_id = generate_album_id(alb_name, tr["artist"], tr.get("year") or "")
                    albums_dict[alb_name] = {
                        "id": album_id,
                        "title": alb_name.upper(),
                        "artist": tr["artist"].upper(),
                        "year": tr.get("year") or time.strftime("%Y"),
                        "format": tr["format"],
                        "qualityTier": tr["qualityTier"],
                        "totalSize": "0 MB",
                        "publisher": tr.get("publisher") or "Telegram Cloud",
                        "coverUrl": tr["cover_url"],
                        "glowColors": color_preset,
                        "tracks": []
                    }
                    album_stats[album_id] = {
                        "total_bytes": 0,
                        "first_track": tr,
                        "hires_track": None,
                    }
                alb_obj = albums_dict[alb_name]
                stats = album_stats[alb_obj["id"]]
                stats["total_bytes"] += int(tr.get("size_bytes", 0) or 0)
                if stats["hires_track"] is None and tr.get("qualityTier") == "hi-res":
                    stats["hires_track"] = tr
                alb_obj["tracks"].append({
                    "id": len(alb_obj["tracks"]) + 1,
                    "name": tr["title"],
                    "artist": tr["artist"],
                    "duration": tr["duration"],
                    "size": tr["size"],
                    "format": tr["format"],
                    "qualityTier": tr["qualityTier"],
                    "bitrate": tr["bitrate"],
                    "audioProbe": tr.get("audioProbe") if isinstance(tr.get("audioProbe"), dict) else {},
                    "previewUrl": tr["stream_url"],
                    "chatId": tr["chat_id"],
                    "msgId": tr["msg_id"],
                    "fileUniqueId": tr.get("file_unique_id", ""),
                    "fingerprint": tr.get("fingerprint", ""),
                    "metadataSource": tr.get("metadata_source", "unknown"),
                    "metadataConfidence": tr.get("metadata_confidence", 0.5),
                    "manualOverride": bool(tr.get("manual_override", False)),
                    "coverUrl": tr["cover_url"],
                    "genre": tr.get("genre") or detect_genre_from_track_info(tr),
                    "country": tr.get("country") or detect_country_from_track_info(tr),
                    "isShazam": bool(tr.get("isShazam", False))
                })
                if tr_idx % 1000 == 0:
                    await asyncio.sleep(0)

            final_albums = list(albums_dict.values())
            for alb_idx, alb in enumerate(final_albums, start=1):
                stats = album_stats.get(alb.get("id"), {})
                alb["totalSize"] = _format_size(int(stats.get("total_bytes", 0) or 0))
                hires_t = stats.get("hires_track")
                first_t = stats.get("first_track")
                if hires_t:
                    alb["format"] = hires_t["format"]
                    alb["qualityTier"] = "hi-res"
                elif first_t:
                    alb["format"] = first_t["format"]
                    alb["qualityTier"] = first_t.get("qualityTier", "lossless")
                
                # Assign country to album
                alb["country"] = detect_country_from_track_info({"name": alb.get("title", ""), "artist": alb.get("artist", ""), "album": alb.get("title", "")})

                for t in alb["tracks"]:
                    if "/api/music/cover/" in t.get("coverUrl", ""):
                        alb["coverUrl"] = t["coverUrl"]
                        break
                if alb_idx % 250 == 0:
                    await asyncio.sleep(0)

            # Lưu vào MongoDB và file JSON
            self._log(
                f"Tổng hợp xong {len(final_albums)} album trong "
                f"{time.time() - finalize_started:.1f}s. Đang lưu cache/database..."
            )
            self._current_track = "Đang lưu thư viện..."
            save_started = time.time()
            changed_album_ids = None
            metadata_to_save = combined_pool
            if mode == "append":
                changed_album_names = {
                    tr.get("album") for tr in all_scanned_tracks if tr.get("album")
                }
                changed_album_ids = {
                    (albums_dict[name].get("id") or "").strip()
                    for name in changed_album_names
                    if name in albums_dict and (albums_dict[name].get("id") or "").strip()
                }
                metadata_to_save = all_scanned_tracks

            await _db_save_library(final_albums, remote_album_ids=changed_album_ids)
            await music_metadata_pipeline.save_many(metadata_to_save, batch_size=1000)

            self._status = "completed"
            self._end_time = time.time()
            self._log(
                f"Đã lưu {len(final_albums)} albums ({len(combined_pool)} bài) trong "
                f"{time.time() - save_started:.1f}s."
            )
        except asyncio.CancelledError:
            self._status = "cancelled"
            self._end_time = time.time()
            self._log("Tiến trình quét đã bị hủy.")
        except Exception as exc:
            self._status = "error"
            self._error_message = str(exc)
            self._end_time = time.time()
            self._log(f"Lỗi trong quá trình quét: {exc}")
            LOGGER.error(f"[MUSIC SCAN ERROR] {exc}", exc_info=True)


music_scan_manager = MusicScanManager()


class MusicAutoSyncManager:
    """Gom sự kiện nhạc mới theo kênh và quét nối tiếp bằng pipeline hiện có."""

    def __init__(self):
        self._pending: dict[str, int] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def _get_channel(self, chat_id: str) -> Optional[dict]:
        target = str(chat_id)
        channels = await _db_load_channels()
        return next((c for c in channels if str(c.get("id")) == target), None)

    async def notify(self, chat_id: str, msg_id: int) -> bool:
        channel = await self._get_channel(chat_id)
        if not channel or not bool(channel.get("auto_sync", False)):
            return False

        target = str(chat_id)
        async with self._lock:
            self._pending[target] = max(int(msg_id), self._pending.get(target, 0))
            task = self._tasks.get(target)
            if not task or task.done():
                self._tasks[target] = asyncio.create_task(self._run_channel(target))
        LOGGER.info(f"[MUSIC AUTO SYNC] Đã nhận bài mới #{msg_id} từ kênh {target}.")
        return True

    async def drop_channel(self, chat_id: str) -> None:
        async with self._lock:
            self._pending.pop(str(chat_id), None)

    async def _run_channel(self, chat_id: str) -> None:
        try:
            # Debounce ngắn để một album được gửi liên tiếp chỉ tạo một lượt scan.
            await asyncio.sleep(1.5)
            while True:
                channel = await self._get_channel(chat_id)
                if not channel or not bool(channel.get("auto_sync", False)):
                    return

                async with self._lock:
                    target_msg_id = int(self._pending.pop(chat_id, 0) or 0)
                if target_msg_id <= 0:
                    return

                last_id = int(channel.get("last_scanned_id", 0) or 0)
                if target_msg_id <= last_id:
                    continue

                # Không tranh pipeline với lượt quét thủ công hoặc kênh auto-sync khác.
                while music_scan_manager.get_status().get("status") == "running":
                    await asyncio.sleep(0.5)
                    channel = await self._get_channel(chat_id)
                    if not channel or not bool(channel.get("auto_sync", False)):
                        return

                result = await music_scan_manager.start(
                    channels=[chat_id],
                    limit=0,
                    resume=False,
                    mode="append",
                    auto_scrape=True,
                    from_msg_id=last_id + 1,
                    to_msg_id=target_msg_id,
                )
                if not result.get("ok"):
                    async with self._lock:
                        self._pending[chat_id] = max(target_msg_id, self._pending.get(chat_id, 0))
                    await asyncio.sleep(1.0)
                    continue

                LOGGER.info(
                    f"[MUSIC AUTO SYNC] Đang đồng bộ kênh {chat_id}: "
                    f"#{last_id + 1} -> #{target_msg_id}."
                )
                while music_scan_manager.get_status().get("status") == "running":
                    await asyncio.sleep(0.5)

                status = music_scan_manager.get_status().get("status")
                if status == "error":
                    LOGGER.error(
                        f"[MUSIC AUTO SYNC] Đồng bộ kênh {chat_id} lỗi: "
                        f"{music_scan_manager.get_status().get('error_message', '')}"
                    )
                    async with self._lock:
                        self._pending[chat_id] = max(target_msg_id, self._pending.get(chat_id, 0))
                    await asyncio.sleep(2.0)
                else:
                    LOGGER.info(f"[MUSIC AUTO SYNC] Đồng bộ kênh {chat_id} hoàn tất tới #{target_msg_id}.")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.error(f"[MUSIC AUTO SYNC] Worker kênh {chat_id} lỗi: {exc}", exc_info=True)
        finally:
            async with self._lock:
                self._tasks.pop(chat_id, None)
                if self._pending.get(chat_id, 0) > 0:
                    channel = await self._get_channel(chat_id)
                    if channel and bool(channel.get("auto_sync", False)):
                        self._tasks[chat_id] = asyncio.create_task(self._run_channel(chat_id))


music_auto_sync_manager = MusicAutoSyncManager()


async def notify_music_auto_sync(chat_id: int, msg_id: int) -> bool:
    """Entry point cho Telegram receiver khi xuất hiện file nhạc mới."""
    return await music_auto_sync_manager.notify(str(chat_id), int(msg_id))


# ── Async Music Scanner APIs ──────────────────────────────────────────────────
@router.post("/api/music/scan/start")
async def start_music_scan_api(payload: dict, _: bool = Depends(require_auth)):
    channels = payload.get("channels") or []
    if not channels and payload.get("chat_id"):
        channels = [payload.get("chat_id")]
    if not channels:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 kênh để quét.")

    from_msg_id = max(0, int(payload.get("from_msg_id", 0) or 0))
    to_msg_id = max(0, int(payload.get("to_msg_id", 0) or 0))

    if from_msg_id > 0:
        resume = False
        limit = 0
    else:
        resume = bool(payload.get("resume", False))
        raw_limit = payload.get("limit", "resume")
        if str(raw_limit).lower() == "resume" or resume:
            limit = -1
            resume = True
        else:
            try:
                val = int(raw_limit)
                limit = 0 if val == 0 else max(val, 5)
            except (ValueError, TypeError):
                limit = 100

    mode = str(payload.get("mode", "append")).lower()
    auto_scrape = bool(payload.get("auto_scrape", True))
    default_artist = str(payload.get("default_artist", "")).strip()
    default_album = str(payload.get("default_album", "")).strip()

    result = await music_scan_manager.start(
        channels=channels,
        limit=limit,
        resume=resume,
        mode=mode,
        auto_scrape=auto_scrape,
        default_artist=default_artist,
        default_album=default_album,
        from_msg_id=from_msg_id,
        to_msg_id=to_msg_id,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result.get("message"))
    return {"status": "success", **result}


@router.get("/api/music/scan/status")
async def get_music_scan_status_api():
    return {"status": "success", "data": music_scan_manager.get_status()}


@router.post("/api/music/scan/cancel")
async def cancel_music_scan_api(_: bool = Depends(require_auth)):
    result = await music_scan_manager.cancel()
    return {"status": "success" if result.get("ok") else "error", **result}


# Endpoint tương thích cũ
@router.post("/api/music/scan")
async def scan_telegram_channel(payload: dict, _: bool = Depends(require_auth)):
    return await start_music_scan_api(payload)


