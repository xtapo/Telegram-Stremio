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

from Backend.fastapi.routes.music.common import GLOW_PRESETS, MUSIC_DATA_DIR, MUSIC_DIR
from Backend.fastapi.routes.music.storage import (
    _db_load_library, _db_save_library, generate_album_id,
)

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ── 6. Xóa Album / Xóa Bài Hát khỏi Thư Viện Cache & MongoDB ─────────────────
@router.delete("/api/music/album/{album_id}")
async def delete_music_album(album_id: str, _: bool = Depends(require_auth)):
    albums = await _db_load_library()
    if not albums:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})
    try:
        new_albums = [a for a in albums if a.get("id") != album_id]
        await _db_save_library(new_albums)
        return JSONResponse(content={"status": "success", "message": "Đã xóa album khỏi thư viện"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.delete("/api/music/track/{chat_id}/{msg_id}")
async def delete_music_track(chat_id: int, msg_id: int, _: bool = Depends(require_auth)):
    albums = await _db_load_library()
    if not albums:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})
    try:
        for a in albums:
            a["tracks"] = [t for t in a.get("tracks", []) if not (int(t.get("chatId", 0)) == int(chat_id) and int(t.get("msgId", 0)) == int(msg_id))]
        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
        await _db_save_library(albums)
        return JSONResponse(content={"status": "success", "message": "Đã xóa bài hát khỏi danh sách"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── 7. Chỉnh Sửa Thông Tin Bài Hát / Album (Edit Metadata) ───────────────────
@router.post("/api/music/track/edit")
async def edit_music_track(payload: dict, _: bool = Depends(require_auth)):
    albums = await _db_load_library()
    if not albums:
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
        target_track = None
        target_album = None
        for a in albums:
            for t in a.get("tracks", []):
                if int(t.get("chatId", 0)) == chat_id and int(t.get("msgId", 0)) == msg_id:
                    target_track = t
                    target_album = a
                    if new_title: t["name"] = new_title
                    if new_artist: t["artist"] = new_artist
                    if new_cover: t["coverUrl"] = new_cover
                    t["metadataSource"] = "manual"
                    t["metadataConfidence"] = 1.0
                    t["manualOverride"] = True
                    t["isShazam"] = False
                    break
            if target_track:
                break

        if not target_track:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy bài hát"})

        if new_album:
            for a in albums:
                a["tracks"] = [t for t in a.get("tracks", []) if not (int(t.get("chatId", 0)) == chat_id and int(t.get("msgId", 0)) == msg_id)]

            dest_album = next((a for a in albums if a.get("title", "").upper() == new_album.upper()), None)
            if not dest_album:
                color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                dest_album = {
                    "id": generate_album_id(new_album, new_artist or target_track.get("artist", "Unknown")),
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
            target_album = dest_album

        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
        await _db_save_library(albums)
        await music_metadata_pipeline.save(
            {
                **target_track,
                "album": (target_album or {}).get("title", new_album),
                "year": (target_album or {}).get("year", ""),
            },
            chat_id=chat_id,
            msg_id=msg_id,
            file_unique_id=target_track.get("fileUniqueId", ""),
            fingerprint=target_track.get("fingerprint", ""),
            source="manual",
            manual_override=True,
            force=True,
        )

        return JSONResponse(content={"status": "success", "message": "Đã cập nhật thông tin bài hát", "albums": albums})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/album/edit")
async def edit_music_album(payload: dict, _: bool = Depends(require_auth)):
    albums = await _db_load_library()
    if not albums:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})

    album_id = payload.get("album_id", "").strip()
    new_title = payload.get("title", "").strip()
    new_artist = payload.get("artist", "").strip()
    new_cover = payload.get("cover_url", "").strip()
    new_year = payload.get("year", "").strip()

    if not album_id or not new_title:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu thông tin album"})

    try:
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

        manual_items = []
        for t in target_album.get("tracks", []):
            t["metadataSource"] = "manual"
            t["metadataConfidence"] = 1.0
            t["manualOverride"] = True
            t["isShazam"] = False
            manual_items.append({
                **t,
                "album": target_album.get("title", ""),
                "year": target_album.get("year", ""),
                "cover_url": t.get("coverUrl") or target_album.get("coverUrl", ""),
                "metadata_source": "manual",
                "metadata_confidence": 1.0,
                "manual_override": True,
            })

        await _db_save_library(albums)
        await music_metadata_pipeline.save_many(manual_items)
        return JSONResponse(content={"status": "success", "message": "Đã cập nhật thông tin album", "albums": albums})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ── 7b. Sửa Hàng Loạt Nhiều Bài Hát Cùng Lúc (Bulk Edit Tracks) ─────────────
@router.post("/api/music/tracks/bulk-edit")
async def bulk_edit_music_tracks(payload: dict, _: bool = Depends(require_auth)):
    albums = await _db_load_library()
    if not albums:
        return JSONResponse(status_code=404, content={"status": "error", "message": "Thư viện trống"})

    track_ids = payload.get("tracks", [])
    new_artist = payload.get("artist", "").strip()
    new_album = payload.get("album", "").strip()
    new_cover = payload.get("cover_url", "").strip()
    new_year = payload.get("year", "").strip()

    if not track_ids:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Chưa chọn bài hát nào"})
    if not new_artist and not new_album and not new_cover and not new_year:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Chưa nhập thông tin cần sửa"})

    id_set = set()
    for tid in track_ids:
        id_set.add((int(tid.get("chatId", 0)), int(tid.get("msgId", 0))))

    try:
        matched_tracks = []
        for a in albums:
            for t in a.get("tracks", []):
                key = (int(t.get("chatId", 0)), int(t.get("msgId", 0)))
                if key in id_set:
                    if new_artist: t["artist"] = new_artist
                    if new_cover: t["coverUrl"] = new_cover
                    t["metadataSource"] = "manual"
                    t["metadataConfidence"] = 1.0
                    t["manualOverride"] = True
                    t["isShazam"] = False
                    matched_tracks.append(t)

        if new_album and matched_tracks:
            for a in albums:
                a["tracks"] = [t for t in a.get("tracks", [])
                               if (int(t.get("chatId", 0)), int(t.get("msgId", 0))) not in id_set]

            dest_album = next((a for a in albums if a.get("title", "").upper() == new_album.upper()), None)
            if not dest_album:
                color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                dest_album = {
                    "id": generate_album_id(new_album, new_artist or matched_tracks[0].get("artist", "Unknown"), new_year or ""),
                    "title": new_album.upper(),
                    "artist": (new_artist or matched_tracks[0].get("artist", "Unknown")).upper(),
                    "year": new_year or time.strftime("%Y"),
                    "format": matched_tracks[0].get("format", "FLAC Hi-Res"),
                    "totalSize": "",
                    "publisher": f"{new_artist or 'Telegram'}",
                    "coverUrl": new_cover or matched_tracks[0].get("coverUrl", ""),
                    "glowColors": color_preset,
                    "tracks": []
                }
                albums.append(dest_album)
            else:
                if new_year: dest_album["year"] = new_year
                if new_cover: dest_album["coverUrl"] = new_cover
                if new_artist: dest_album["artist"] = new_artist.upper()

            dest_album["tracks"].extend(matched_tracks)
        else:
            if new_year or new_cover or new_artist:
                for a in albums:
                    if any((int(t.get("chatId", 0)), int(t.get("msgId", 0))) in id_set for t in a.get("tracks", [])):
                        if new_year: a["year"] = new_year
                        if new_cover: a["coverUrl"] = new_cover
                        if new_artist: a["artist"] = new_artist.upper()

        albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
        manual_items = []
        for a in albums:
            for t in a.get("tracks", []):
                key = (int(t.get("chatId", 0)), int(t.get("msgId", 0)))
                if key in id_set:
                    manual_items.append({
                        **t,
                        "album": a.get("title", ""),
                        "year": a.get("year", ""),
                        "cover_url": t.get("coverUrl") or a.get("coverUrl", ""),
                        "metadata_source": "manual",
                        "metadata_confidence": 1.0,
                        "manual_override": True,
                    })
        await _db_save_library(albums)
        await music_metadata_pipeline.save_many(manual_items)

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


# ── Real-time Background Music Shazam Manager ────────────────────────────────
class MusicShazamManager:
    def __init__(self):
        self._status = "idle"  # idle, running, completed, cancelled, error
        self._total = 0
        self._current = 0
        self._success_count = 0
        self._failed_count = 0
        self._current_track = ""
        self._error_message = ""
        self._logs = []
        self._task = None
        self._start_time = None
        self._end_time = None

    def get_status(self) -> dict:
        pct = 0
        if self._total > 0:
            pct = min(100, round((self._current / self._total) * 100))
        if self._status == "completed":
            pct = 100

        return {
            "status": self._status,
            "total": self._total,
            "current": self._current,
            "percent": pct,
            "success_count": self._success_count,
            "failed_count": self._failed_count,
            "current_track": self._current_track,
            "error_message": self._error_message,
            "logs": self._logs[-60:],  # Giữ 60 logs gần nhất
            "start_time": self._start_time,
            "end_time": self._end_time
        }

    def _add_log(self, text: str, log_type: str = "info"):
        self._logs.append({
            "time": time.strftime("%H:%M:%S"),
            "msg": text,
            "type": log_type
        })
        if len(self._logs) > 200:
            self._logs = self._logs[-200:]

    async def start(self, tracks: list) -> dict:
        if self._status == "running" and self._task and not self._task.done():
            return {"ok": False, "message": "Đang có tiến trình nhận diện Đa Lớp đang chạy!"}

        self._status = "running"
        self._total = len(tracks)
        self._current = 0
        self._success_count = 0
        self._failed_count = 0
        self._current_track = "Đang khởi động..."
        self._error_message = ""
        self._logs = []
        self._start_time = time.time()
        self._end_time = None

        self._add_log(f"Bắt đầu nhận diện Đa Lớp cho {self._total} bài hát (Embedded tags + fingerprint cache + Shazam đa mẫu + Apple Music & Deezer)...", "info")
        self._task = asyncio.create_task(self._run_worker(tracks))
        return {"ok": True, "message": f"Đã bắt đầu nhận diện {self._total} bài hát."}

    async def cancel(self) -> dict:
        if self._status != "running" or not self._task:
            return {"ok": False, "message": "Không có tiến trình nào đang chạy."}

        self._task.cancel()
        self._status = "cancelled"
        self._end_time = time.time()
        self._add_log("Tiến trình nhận diện đã được dừng theo yêu cầu của bạn.", "warn")
        return {"ok": True, "message": "Đã hủy tiến trình nhận diện thành công."}

    async def _run_worker(self, tracks: list):
        try:
            from Backend.helper.metadata.audio_fingerprint import recognize_audio_from_telegram
            from Backend.helper.metadata.music_scraper import fetch_music_metadata

            albums = await _db_load_library()
            if not albums:
                self._status = "error"
                self._error_message = "Thư viện nhạc trống"
                self._add_log("Thư viện nhạc trống, không thể tiếp tục.", "error")
                return

            for idx, t in enumerate(tracks, 1):
                self._current = idx
                chat_id = t.get("chatId")
                msg_id = t.get("msgId")
                orig_name = t.get("name") or f"Bài hát #{msg_id}"

                try:
                    chat_id_int = int(chat_id)
                    msg_id_int = int(msg_id)
                except Exception:
                    self._failed_count += 1
                    self._add_log(f"⚠️ #{idx} ID không hợp lệ: {orig_name}", "warn")
                    continue

                curr_track = None
                curr_album = None
                for a in albums:
                    for tr in a.get("tracks", []):
                        if int(tr.get("chatId", 0)) == chat_id_int and int(tr.get("msgId", 0)) == msg_id_int:
                            curr_track = tr
                            curr_album = a
                            if not t.get("name"):
                                orig_name = tr.get("name", orig_name)
                            break
                    if curr_track:
                        break

                self._current_track = orig_name
                self._add_log(f"🔍 #{idx}/{self._total} Phân tích đa lớp: {orig_name}...", "info")

                def _track_log(msg_text: str, lvl: str = "info"):
                    self._add_log(f"  ↳ #{idx} {msg_text}", lvl)

                # Lớp 1 & Lớp 2 & Lớp 3: Vân tay Shazam + Thẻ ID3 gốc + Apple Music & Deezer trực tuyến
                h_name = curr_track.get("name") if curr_track else orig_name
                h_artist = curr_track.get("artist") if curr_track else None
                h_album = curr_album.get("title") if curr_album else None

                fg_res = await recognize_audio_from_telegram(
                    client=None,
                    message=None,
                    is_manual=True,
                    chat_id=chat_id_int,
                    msg_id=msg_id_int,
                    log_callback=_track_log,
                    hint_title=h_name,
                    hint_artist=h_artist,
                    hint_album=h_album,
                )
                await asyncio.sleep(0.15)

                # Nếu nhận diện qua ID3 tag mà chưa có cover HD, tìm bù cover từ Apple Music / Deezer
                if fg_res and not fg_res.get("cover_url"):
                    try:
                        sc_cover = await fetch_music_metadata(
                            raw_title=fg_res.get("title", ""),
                            raw_artist=fg_res.get("artist", ""),
                            file_name=orig_name
                        )
                        if sc_cover and sc_cover.get("cover_url"):
                            fg_res["cover_url"] = sc_cover["cover_url"]
                            if not fg_res.get("album") or "Single" in fg_res.get("album", ""):
                                fg_res["album"] = sc_cover.get("album") or fg_res.get("album")
                            if not fg_res.get("genre"):
                                fg_res["genre"] = sc_cover.get("genre")
                    except Exception:
                        pass

                # Nếu tất cả các lớp không khớp, thông báo chi tiết
                if not fg_res:
                    _track_log("⚠️ Không tìm thấy kết quả khớp trên Shazam (vân tay), Thẻ ID3 gốc hoặc kho nhạc trực tuyến.", "warn")

                if fg_res:
                    matched_layer = fg_res.get("layer", "Đa Lớp")
                    recognized_source = normalize_metadata_source(fg_res.get("source"))
                    recognized_confidence = metadata_confidence(
                        recognized_source,
                        fg_res.get("confidence"),
                    )
                    is_audio_shazam = recognized_source == "shazam"
                    update_fields = {}
                    if fg_res.get("title"): update_fields["name"] = fg_res["title"]
                    if fg_res.get("artist"): update_fields["artist"] = fg_res["artist"]
                    if fg_res.get("album"): update_fields["album"] = fg_res["album"]
                    if fg_res.get("cover_url"): update_fields["coverUrl"] = fg_res["cover_url"]
                    if fg_res.get("fingerprint"): update_fields["fingerprint"] = fg_res["fingerprint"]
                    update_fields["metadataSource"] = recognized_source
                    update_fields["metadataConfidence"] = recognized_confidence
                    update_fields["manualOverride"] = False
                    update_fields["isShazam"] = is_audio_shazam

                    if update_fields:
                        updated = False
                        for a in albums:
                            for tr in a.get("tracks", []):
                                if int(tr.get("chatId", 0)) == chat_id_int and int(tr.get("msgId", 0)) == msg_id_int:
                                    for k, v in update_fields.items():
                                        tr[k] = v
                                    updated = True

                                    new_album_name = update_fields.get("album")
                                    if new_album_name and new_album_name != a.get("title"):
                                        a["tracks"].remove(tr)
                                        dest_album = next((al for al in albums if al.get("title") == new_album_name), None)
                                        if not dest_album:
                                            import secrets
                                            import random
                                            color_preset = random.choice(GLOW_PRESETS)
                                            dest_album = {
                                                "id": f"album_{secrets.token_hex(4)}",
                                                "title": new_album_name,
                                                "artist": update_fields.get("artist", "").upper(),
                                                "year": "2026",
                                                "format": tr.get("format", ""),
                                                "qualityTier": tr.get("qualityTier", "standard"),
                                                "publisher": f"{update_fields.get('artist', '') or 'Telegram'}",
                                                "coverUrl": update_fields.get("coverUrl") or tr.get("coverUrl", ""),
                                                "glowColors": color_preset,
                                                "tracks": []
                                            }
                                            albums.append(dest_album)
                                        dest_album["tracks"].append(tr)

                                    break
                            if updated:
                                break
                        if updated:
                            self._success_count += 1
                            await music_metadata_pipeline.save(
                                {
                                    **(curr_track or {}),
                                    "title": fg_res.get("title") or (curr_track or {}).get("name", ""),
                                    "artist": fg_res.get("artist") or (curr_track or {}).get("artist", ""),
                                    "album": fg_res.get("album") or (curr_album or {}).get("title", ""),
                                    "cover_url": fg_res.get("cover_url") or (curr_track or {}).get("coverUrl", ""),
                                    "genre": fg_res.get("genre") or (curr_track or {}).get("genre", ""),
                                    "fingerprint": fg_res.get("fingerprint") or (curr_track or {}).get("fingerprint", ""),
                                    "metadata_source": recognized_source,
                                    "metadata_confidence": recognized_confidence,
                                    "manual_override": False,
                                },
                                chat_id=chat_id_int,
                                msg_id=msg_id_int,
                                file_unique_id=(curr_track or {}).get("fileUniqueId", ""),
                                fingerprint=fg_res.get("fingerprint") or (curr_track or {}).get("fingerprint", ""),
                                source=recognized_source,
                                manual_override=False,
                                force=True,
                            )
                            genre_str = f" [{fg_res.get('genre')}]" if fg_res.get('genre') else ""
                            self._add_log(f"✅ #{idx} [{matched_layer}] {fg_res.get('title')} - {fg_res.get('artist')}{genre_str}", "success")
                else:
                    self._failed_count += 1
                    self._add_log(f"⚠️ #{idx} {orig_name}: Tất cả các lớp nhận diện đều không khớp", "warn")

                # Lưu trung gian mỗi 5 bài
                if idx % 5 == 0 and self._success_count > 0:
                    try:
                        valid_albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
                        await _db_save_library(valid_albums, sync_remote=False)
                    except Exception:
                        pass

            # Lưu thư viện cuối cùng
            if self._success_count > 0:
                albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
                await _db_save_library(albums, wait_remote=False)

            self._status = "completed"
            self._end_time = time.time()
            self._add_log(f"🎉 Hoàn tất nhận diện! {self._success_count}/{self._total} bài hát thành công.", "success")
        except asyncio.CancelledError:
            self._status = "cancelled"
            self._end_time = time.time()
            self._add_log("Tiến trình nhận diện đã dừng.", "warn")
        except Exception as exc:
            self._status = "error"
            self._error_message = str(exc)
            self._end_time = time.time()
            self._add_log(f"Lỗi: {exc}", "error")
            LOGGER.error(f"[SHAZAM ERROR] {exc}", exc_info=True)


music_shazam_manager = MusicShazamManager()


@router.post("/api/music/tracks/shazam")
@router.post("/api/music/tracks/shazam/start")
async def start_shazam_identification(request: Request, _: bool = Depends(require_auth)):
    try:
        data = await request.json()
        tracks = data.get("tracks", [])
        if not tracks:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Không có bài hát nào được cung cấp."})

        res = await music_shazam_manager.start(tracks)
        if not res.get("ok"):
            return JSONResponse(status_code=409, content={"status": "error", "message": res.get("message")})
        return JSONResponse(content={"status": "success", "message": res.get("message"), "data": music_shazam_manager.get_status()})
    except Exception as e:
        LOGGER.error(f"[SHAZAM API] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/music/tracks/shazam/status")
async def get_shazam_status_api():
    return JSONResponse(content={"status": "success", "data": music_shazam_manager.get_status()})


@router.post("/api/music/tracks/shazam/cancel")
async def cancel_shazam_api(_: bool = Depends(require_auth)):
    res = await music_shazam_manager.cancel()
    return JSONResponse(content={"status": "success" if res.get("ok") else "error", "message": res.get("message")})


# ── 9. Quản Lý Thông Tin & Ảnh Nghệ Sĩ (Artist Metadata & Images) ────────────

def _normalize_country_name(country_raw: str, country_code: str = "") -> str:
    """
    Chuẩn hóa tên quốc gia từ các nguồn API (TheAudioDB, MusicBrainz, Last.fm)
    về bộ phân loại chuẩn của hệ thống:
    'Việt Nam', 'Âu Mỹ', 'Hàn Quốc', 'Hoa Ngữ', 'Nhật Bản', 'Thái Lan', 'Latin / Tây Ban Nha', 'Pháp / Châu Âu', 'Quốc Tế'
    """
    if not country_raw and not country_code:
        return ""
    
    code = (country_code or "").upper().strip()
    c = (country_raw or "").lower().strip()
    
    # 1. Việt Nam
    if code == "VN" or "vietnam" in c or "việt nam" in c or "viet nam" in c:
        return "Việt Nam"
    
    # 2. Hàn Quốc
    if code in ["KR", "KP"] or "korea" in c or "hàn quốc" in c or "south korea" in c:
        return "Hàn Quốc"
        
    # 3. Nhật Bản
    if code == "JP" or "japan" in c or "nhật bản" in c or "nippon" in c:
        return "Nhật Bản"
        
    # 4. Hoa Ngữ
    if code in ["CN", "TW", "HK", "MO"] or "china" in c or "taiwan" in c or "hong kong" in c or "hoa ngữ" in c or "trung quốc" in c or "đài loan" in c:
        return "Hoa Ngữ"
        
    # 5. Thái Lan
    if code == "TH" or "thailand" in c or "thái lan" in c or "thai" in c:
        return "Thái Lan"
        
    # 6. Pháp / Châu Âu
    if code in ["FR", "BE", "CH", "MC"] or "france" in c or "french" in c or "pháp" in c or "belgium" in c or "switzerland" in c:
        return "Pháp / Châu Âu"
        
    # 7. Latin / Tây Ban Nha
    if code in ["ES", "MX", "CO", "AR", "PR", "BR", "CL", "PE", "VE", "CU", "DO", "GT", "EC"] or any(k in c for k in ["spain", "mexico", "colombia", "argentina", "puerto rico", "brazil", "latin", "chile", "peru", "tây ban nha"]):
        return "Latin / Tây Ban Nha"
        
    # 8. Âu Mỹ (US, UK, CA, AU, NZ, DE, IT, NL, SE, NO, DK, FI, IE, AT, PL, etc.)
    if code in ["US", "GB", "UK", "CA", "AU", "NZ", "DE", "IT", "NL", "SE", "NO", "DK", "FI", "IE", "AT", "PL", "RU", "UA", "CZ", "GR", "PT", "RO", "HU"] or any(k in c for k in ["united states", "united kingdom", "great britain", "england", "scotland", "canada", "australia", "germany", "sweden", "norway", "netherlands", "italy", "ireland", "denmark", "finland", "new zealand", "austria", "russia", "âu mỹ", "american", "british", "usa"]):
        return "Âu Mỹ"
        
    return "Quốc Tế"


async def _search_artist_online_helper(name: str):
    """
    Tìm kiếm thông tin, ảnh chân dung, ảnh fanart 1080p, banner, quốc gia và tiểu sử (Bio)
    từ Deezer, TheAudioDB, MusicBrainz, Last.fm và Apple Music
    """
    import httpx
    import urllib.parse
    import re

    results = []
    seen_urls = set()
    cleaned_name = name.strip()
    if not cleaned_name:
        return results

    # 1. Deezer Artist Search (Ảnh chân dung vuông HD 1000x1000)
    try:
        url = f"https://api.deezer.com/search/artist?q={urllib.parse.quote(cleaned_name)}&limit=6"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                for art in data.get("data", []):
                    art_name = art.get("name", "")
                    pic_xl = art.get("picture_xl") or art.get("picture_big") or art.get("picture_medium")
                    if pic_xl and pic_xl not in seen_urls:
                        seen_urls.add(pic_xl)
                        results.append({
                            "name": art_name,
                            "avatar_url": pic_xl,
                            "banner_url": art.get("picture_xl") or pic_xl,
                            "preview_url": art.get("picture_medium", pic_xl),
                            "fans_count": art.get("nb_fan", 0),
                            "nb_album": art.get("nb_album", 0),
                            "type": "portrait",
                            "source": "Deezer"
                        })
    except Exception as e:
        LOGGER.warning(f"[ARTIST SEARCH] Deezer search error for '{cleaned_name}': {e}")

    # 2. TheAudioDB (Ảnh chân dung, Fanart nền 1080p, Banner, Quốc Gia, Tiểu sử)
    try:
        tadb_url = f"https://www.theaudiodb.com/api/v1/json/2/search.php?s={urllib.parse.quote(cleaned_name)}"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(tadb_url)
            if resp.status_code == 200:
                data = resp.json()
                for art in (data.get("artists") or []):
                    art_name = art.get("strArtist", cleaned_name)
                    bio_vi = art.get("strBiographyVI") or ""
                    bio_en = art.get("strBiographyEN") or ""
                    bio = bio_vi if bio_vi else bio_en
                    genre = art.get("strGenre") or ""
                    str_country = art.get("strCountry") or ""
                    str_country_code = art.get("strCountryCode") or ""
                    country_normalized = _normalize_country_name(str_country, str_country_code)
                    
                    thumb = art.get("strArtistThumb")
                    if thumb and thumb not in seen_urls:
                        seen_urls.add(thumb)
                        results.append({
                            "name": art_name,
                            "avatar_url": thumb,
                            "banner_url": art.get("strArtistFanart") or thumb,
                            "preview_url": thumb,
                            "bio": bio,
                            "genre": genre,
                            "country": country_normalized,
                            "country_raw": str_country,
                            "type": "portrait",
                            "source": "TheAudioDB"
                        })
                    
                    fanart = art.get("strArtistFanart")
                    if fanart and fanart not in seen_urls:
                        seen_urls.add(fanart)
                        results.append({
                            "name": f"{art_name} (Fanart)",
                            "avatar_url": fanart,
                            "banner_url": fanart,
                            "preview_url": fanart,
                            "bio": bio,
                            "genre": genre,
                            "country": country_normalized,
                            "type": "fanart",
                            "source": "TheAudioDB Fanart"
                        })
    except Exception as e:
        LOGGER.warning(f"[ARTIST SEARCH] TheAudioDB error for '{cleaned_name}': {e}")

    # 3. MusicBrainz API (Kho cơ sở dữ liệu nghệ sĩ nguồn mở quốc tế - Tra cứu Quốc Gia chuẩn xác)
    try:
        mb_url = f"https://musicbrainz.org/ws/2/artist/?query=artist:{urllib.parse.quote(cleaned_name)}&fmt=json&limit=3"
        mb_headers = {"User-Agent": "XTAPOMusic/1.0 ( support@xtapo.com )"}
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            resp = await client.get(mb_url, headers=mb_headers)
            if resp.status_code == 200:
                mb_data = resp.json()
                for mb_art in mb_data.get("artists", []):
                    mb_country = mb_art.get("country", "")
                    mb_area = (mb_art.get("area") or {}).get("name", "") or (mb_art.get("begin-area") or {}).get("name", "")
                    mb_c = _normalize_country_name(mb_area, mb_country)
                    if mb_c:
                        results.append({
                            "name": mb_art.get("name", cleaned_name),
                            "country": mb_c,
                            "country_code": mb_country,
                            "area": mb_area,
                            "type": "meta",
                            "source": "MusicBrainz"
                        })
                        break
    except Exception as e:
        LOGGER.debug(f"[ARTIST SEARCH] MusicBrainz query note for '{cleaned_name}': {e}")

    # 4. Last.fm (Tiểu sử phong phú + Danh sách Tags Thể Loại)
    try:
        lfm_url = f"https://ws.audioscrobbler.com/2.0/?method=artist.getinfo&artist={urllib.parse.quote(cleaned_name)}&api_key=b25b959554ed76058ac220b7b2e0a026&format=json"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(lfm_url)
            if resp.status_code == 200:
                data = resp.json()
                art = data.get("artist")
                if art:
                    raw_bio = art.get("bio", {}).get("summary", "")
                    clean_bio = re.sub(r'<a[^>]*>.*?</a>', '', raw_bio).strip() if raw_bio else ""
                    raw_tags = [t.get("name") for t in art.get("tags", {}).get("tag", []) if t.get("name")]
                    
                    results.append({
                        "name": art.get("name", cleaned_name),
                        "bio": clean_bio,
                        "tags": raw_tags,
                        "listeners": art.get("stats", {}).get("listeners", 0),
                        "source": "Last.fm"
                    })
    except Exception as e:
        LOGGER.warning(f"[ARTIST SEARCH] Last.fm error for '{cleaned_name}': {e}")

    # 5. Apple Music / iTunes (Tìm thêm thể loại chính thức)
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(cleaned_name)}&entity=musicArtist&limit=4"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("results", []):
                    results.append({
                        "name": item.get("artistName", ""),
                        "primary_genre": item.get("primaryGenreName", ""),
                        "source": "Apple Music"
                    })
    except Exception as e:
        LOGGER.warning(f"[ARTIST SEARCH] iTunes artist error for '{cleaned_name}': {e}")

    return results


_IN_MEMORY_ARTISTS_CACHE: Optional[list] = None
_IN_MEMORY_ARTISTS_CACHE_TIME: float = 0.0
ARTISTS_CACHE_TTL = 3600  # 1 giờ (tự động invalidate khi có cập nhật)
ARTISTS_CACHE_FILE = os.path.join(MUSIC_DATA_DIR, "artists_cache.json")
LEGACY_ARTISTS_CACHE_FILE = os.path.join(MUSIC_DIR, "artists_cache.json")

def _invalidate_artists_cache():
    global _IN_MEMORY_ARTISTS_CACHE, _IN_MEMORY_ARTISTS_CACHE_TIME
    _IN_MEMORY_ARTISTS_CACHE = None
    _IN_MEMORY_ARTISTS_CACHE_TIME = 0.0
    for p in [ARTISTS_CACHE_FILE, LEGACY_ARTISTS_CACHE_FILE]:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

def _load_artists_file_cache() -> list | None:
    for p in [ARTISTS_CACHE_FILE, LEGACY_ARTISTS_CACHE_FILE]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception:
                pass
    return None

def _save_artists_file_cache(artists: list):
    for p in [ARTISTS_CACHE_FILE, LEGACY_ARTISTS_CACHE_FILE]:
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(artists, f, ensure_ascii=False)
        except Exception:
            pass


@router.get("/api/music/artists")
async def get_all_artists(force_refresh: bool = False):
    """
    Lấy danh sách tất cả ca sĩ được trích xuất từ thư viện nhạc kèm ảnh, quốc gia và metadata
    (Tự động cache RAM + SSD để phản hồi tức thì < 1ms)
    """
    global _IN_MEMORY_ARTISTS_CACHE, _IN_MEMORY_ARTISTS_CACHE_TIME
    now = time.time()

    # 1. Kiểm tra cache RAM (< 0.1ms)
    if not force_refresh and _IN_MEMORY_ARTISTS_CACHE is not None:
        if now - _IN_MEMORY_ARTISTS_CACHE_TIME < ARTISTS_CACHE_TTL:
            return JSONResponse(content={"status": "success", "count": len(_IN_MEMORY_ARTISTS_CACHE), "artists": _IN_MEMORY_ARTISTS_CACHE})

    # 2. Kiểm tra file cache SSD (< 2ms)
    if not force_refresh:
        file_cached = _load_artists_file_cache()
        if file_cached:
            _IN_MEMORY_ARTISTS_CACHE = file_cached
            _IN_MEMORY_ARTISTS_CACHE_TIME = now
            return JSONResponse(content={"status": "success", "count": len(file_cached), "artists": file_cached})

    try:
        albums = await _db_load_library()
        artist_map = {}
        
        # 1. Thu thập ca sĩ từ albums và tracks
        for a in albums:
            alb_artist = (a.get("artist") or "Unknown Artist").strip()
            alb_title = a.get("title", "")
            for t in a.get("tracks", []):
                t_artist = (t.get("artist") or alb_artist or "Unknown Artist").strip()
                if not t_artist:
                    continue
                if t_artist not in artist_map:
                    artist_map[t_artist] = {
                        "name": t_artist,
                        "tracks_count": 0,
                        "albums": set(),
                        "genres": set(),
                        "sample_track_cover": t.get("coverUrl") or a.get("coverUrl", "")
                    }
                artist_map[t_artist]["tracks_count"] += 1
                if alb_title:
                    artist_map[t_artist]["albums"].add(alb_title)
                if t.get("genre"):
                    artist_map[t_artist]["genres"].add(t.get("genre").strip())

        # 2. Lấy metadata đã cache từ MongoDB collection `music_artists` (dùng projection để tải cực nhanh)
        cached_map = {}
        try:
            if db and hasattr(db, "dbs") and "tracking" in db.dbs:
                coll = db.dbs["tracking"]["music_artists"]
                cached_cursor = coll.find(
                    {},
                    projection={"_id": 1, "avatar_url": 1, "banner_url": 1, "bio": 1, "country": 1, "genres": 1, "fans_count": 1}
                )
                async for doc in cached_cursor:
                    cached_map[doc["_id"]] = doc
        except Exception as e:
            LOGGER.warning(f"[GET ARTISTS] Could not read cached artists from MongoDB: {e}")

        # 3. Tổng hợp kết quả (loại bỏ albums_list để giảm payload mạng từ 4MB xuống ~300KB)
        artists_list = []
        for name, data in artist_map.items():
            slug = name.lower().strip()
            cached = cached_map.get(slug) or cached_map.get(name)
            
            avatar_url = (cached.get("avatar_url") if cached else "") or data["sample_track_cover"] or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop"
            banner_url = (cached.get("banner_url") if cached else "") or avatar_url
            bio = cached.get("bio", "") if cached else ""
            country = cached.get("country", "") if cached else ""
            genres = list(set(list(data["genres"]) + (cached.get("genres", []) if cached else [])))

            artists_list.append({
                "name": name,
                "avatar_url": avatar_url,
                "banner_url": banner_url,
                "bio": bio,
                "country": country,
                "genres": genres,
                "fans_count": cached.get("fans_count", 0) if cached else 0,
                "has_custom_avatar": bool(cached and cached.get("avatar_url")),
                "tracks_count": data["tracks_count"],
                "albums_count": len(data["albums"])
            })

        artists_list.sort(key=lambda x: x["tracks_count"], reverse=True)

        # 4. Cập nhật cache RAM & file cache SSD
        _IN_MEMORY_ARTISTS_CACHE = artists_list
        _IN_MEMORY_ARTISTS_CACHE_TIME = now
        _save_artists_file_cache(artists_list)

        return JSONResponse(content={"status": "success", "count": len(artists_list), "artists": artists_list})
    except Exception as e:
        LOGGER.error(f"[GET ARTISTS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/music/artist/search-online")
async def search_artist_online(name: str = Query(..., min_length=1), _: bool = Depends(require_auth)):
    """
    Tìm kiếm ảnh chân dung và profile ca sĩ từ Deezer / TheAudioDB / MusicBrainz / Apple Music
    """
    try:
        results = await _search_artist_online_helper(name)
        return JSONResponse(content={"status": "success", "count": len(results), "results": results})
    except Exception as e:
        LOGGER.error(f"[SEARCH ARTIST ONLINE] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/artist/update")
async def update_artist_metadata(payload: dict, _: bool = Depends(require_auth)):
    """
    Admin cập nhật thông tin, quốc gia và ảnh đại diện cho ca sĩ
    """
    name = payload.get("name", "").strip()
    avatar_url = payload.get("avatar_url", "").strip()
    banner_url = payload.get("banner_url", "").strip()
    bio = payload.get("bio", "").strip()
    country = payload.get("country", "").strip()
    genres = payload.get("genres", [])

    if not name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Tên ca sĩ là bắt buộc."})

    try:
        coll = db.dbs["tracking"]["music_artists"]
        slug = name.lower().strip()
        
        update_data = {
            "name": name,
            "avatar_url": avatar_url,
            "banner_url": banner_url or avatar_url,
            "bio": bio,
            "country": country,
            "genres": genres if isinstance(genres, list) else [],
            "updated_at": time.time()
        }
        
        await coll.update_one({"_id": slug}, {"$set": update_data}, upsert=True)
        _invalidate_artists_cache()
        return JSONResponse(content={"status": "success", "message": f"Đã cập nhật thông tin ca sĩ '{name}' thành công."})
    except Exception as e:
        LOGGER.error(f"[UPDATE ARTIST] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/artists/auto-fetch")
async def auto_fetch_artists_metadata(_: bool = Depends(require_auth)):
    """
    Tiến trình quét ngầm tự động tìm & lưu ảnh chân dung HD, fanart, quốc gia, bio và thể loại cho toàn bộ ca sĩ trong thư viện
    kết hợp 5 nguồn: TheAudioDB, MusicBrainz, Deezer, Last.fm và Apple Music
    """
    try:
        albums = await _db_load_library()
        artists_to_search = set()
        
        for a in albums:
            if a.get("artist"):
                artists_to_search.add(a["artist"].strip())
            for t in a.get("tracks", []):
                if t.get("artist"):
                    artists_to_search.add(t["artist"].strip())

        coll = db.dbs["tracking"]["music_artists"]
        updated_count = 0
        
        for art_name in artists_to_search:
            if not art_name or art_name.lower() in ["unknown", "unknown artist", "va", "various artists", "various artist", "nhiều ca sĩ", "nhạc tuyển chọn"]:
                continue
                
            slug = art_name.lower().strip()
            existing = await coll.find_one({"_id": slug})
            if existing and existing.get("avatar_url") and existing.get("bio") and existing.get("country"):
                continue  # Đã có đầy đủ ảnh, tiểu sử và quốc gia
                
            matches = await _search_artist_online_helper(art_name)
            if matches:
                # 1. Tìm avatar tốt nhất (ưu tiên ảnh chân dung Deezer / TheAudioDB)
                avatar_match = next((m for m in matches if m.get("avatar_url") and m.get("type") == "portrait"), None)
                if not avatar_match:
                    avatar_match = next((m for m in matches if m.get("avatar_url")), None)
                
                # 2. Tìm fanart banner tốt nhất
                fanart_match = next((m for m in matches if m.get("banner_url") and m.get("type") == "fanart"), None)
                
                # 3. Tìm bio tốt nhất
                bio_match = next((m for m in matches if m.get("bio")), None)
                
                # 4. Tìm quốc gia từ TheAudioDB hoặc MusicBrainz
                country_match = next((m["country"] for m in matches if m.get("country")), "")
                
                # 5. Gom thể loại
                genres = []
                for m in matches:
                    if m.get("tags"):
                        for t in m["tags"][:4]:
                            if t and t.title() not in genres: genres.append(t.title())
                    if m.get("genre") and m["genre"] not in genres:
                        genres.append(m["genre"])
                    if m.get("primary_genre") and m["primary_genre"] not in genres:
                        genres.append(m["primary_genre"])

                avatar_url = avatar_match["avatar_url"] if avatar_match else (existing.get("avatar_url") if existing else "")
                banner_url = fanart_match["banner_url"] if fanart_match else (avatar_match.get("banner_url") if avatar_match else avatar_url)
                bio = bio_match["bio"] if bio_match else (existing.get("bio") if existing else "")
                country = country_match or (existing.get("country") if existing else "")
                
                if avatar_url or bio or genres or country:
                    doc = {
                        "name": art_name,
                        "avatar_url": avatar_url,
                        "banner_url": banner_url or avatar_url,
                        "bio": bio,
                        "country": country,
                        "genres": genres[:5],
                        "fans_count": avatar_match.get("fans_count", 0) if avatar_match else 0,
                        "source": "Deezer + TheAudioDB + MusicBrainz + Last.fm",
                        "updated_at": time.time()
                    }
                    await coll.update_one({"_id": slug}, {"$set": doc}, upsert=True)
                    updated_count += 1
            
            # Nghỉ nhẹ 100ms tránh rate-limit
            import asyncio
            await asyncio.sleep(0.1)

        if updated_count > 0:
            _invalidate_artists_cache()

        return JSONResponse(content={
            "status": "success", 
            "count": updated_count, 
            "message": f"Đã tự động tải và cập nhật ảnh chân dung HD, Fanart, Quốc Gia & Tiểu sử cho {updated_count} ca sĩ!"
        })
    except Exception as e:
        LOGGER.error(f"[AUTO FETCH ARTISTS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})




def invalidate_artists_cache() -> None:
    _invalidate_artists_cache()
