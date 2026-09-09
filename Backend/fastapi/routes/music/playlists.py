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

from Backend.fastapi.routes.music.common import MUSIC_DATA_DIR, MUSIC_DIR
from Backend.fastapi.routes.music.audio import detect_genre_from_track_info
from Backend.fastapi.routes.music.storage import _db_load_library, _db_save_library

router = APIRouter(tags=["Music Player & Telegram Storage"])

PLAYLISTS_FILE = os.path.join(MUSIC_DATA_DIR, "telegram_playlists.json")
LEGACY_PLAYLISTS_FILE = os.path.join(MUSIC_DIR, "telegram_playlists.json")

def _load_playlists_file() -> list:
    for path in [PLAYLISTS_FILE, LEGACY_PLAYLISTS_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
    return []


def _save_playlists_file(playlists: list):
    for path in [PLAYLISTS_FILE, LEGACY_PLAYLISTS_FILE]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(playlists, f, ensure_ascii=False, indent=2)
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to save playlists to {path}: {e}")


# ── 2. Lấy danh sách Albums & Tracks từ MongoDB / Telegram Cache ───────────────
@router.get("/api/music/albums")
async def get_music_albums():
    data = await _db_load_library()
    return JSONResponse(content={"status": "success", "source": "database", "albums": data or []})

@router.post("/api/music/reclassify-genres")
async def reclassify_library_genres():
    """Tự động phân loại lại toàn bộ thể loại cho các bài hát đã có trong thư viện"""
    data = await _db_load_library()
    if not data:
        return JSONResponse(content={"status": "empty", "message": "Thư viện trống"})

    genre_counts = {}
    updated_count = 0
    total_tracks = 0

    for alb in data:
        for t in alb.get("tracks", []):
            total_tracks += 1
            t["album"] = alb.get("title", "")
            new_genre = detect_genre_from_track_info(t)
            if t.get("genre") != new_genre:
                t["genre"] = new_genre
                updated_count += 1
            genre_counts[new_genre] = genre_counts.get(new_genre, 0) + 1

    await _db_save_library(data)
    LOGGER.info(f"[MUSIC GENRES] Đã phân loại lại {updated_count}/{total_tracks} bài hát theo 16 thể loại mới.")
    return JSONResponse(content={
        "status": "success",
        "message": f"Đã phân loại lại {total_tracks} bài hát!",
        "updated_tracks": updated_count,
        "total_tracks": total_tracks,
        "genre_breakdown": genre_counts
    })


# ── Direct M3U8 Playlist Stream Endpoints (VLC, PotPlayer, Foobar2000, Apple Music) ──

_SHARED_M3U8_CACHE: Dict[str, dict] = {}

DEMO_ALBUMS_FALLBACK = [
    {
        "id": "shania-twain-little-miss-twain",
        "title": "LITTLE MISS TWAIN",
        "artist": "SHANIA TWAIN",
        "tracks": [
            { "id": 1, "name": "Any Man of Mine (Little Miss Twain Edition)", "artist": "SHANIA TWAIN", "duration": "4:07", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" },
            { "id": 2, "name": "That Don't Impress Me Much", "artist": "SHANIA TWAIN", "duration": "3:59", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3" },
            { "id": 3, "name": "Man! I Feel Like a Woman!", "artist": "SHANIA TWAIN", "duration": "3:53", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3" },
            { "id": 4, "name": "You're Still the One", "artist": "SHANIA TWAIN", "duration": "3:32", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3" },
            { "id": 5, "name": "From This Moment On", "artist": "SHANIA TWAIN", "duration": "4:43", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3" }
        ]
    },
    {
        "id": "shania-twain-come-on-over",
        "title": "COME ON OVER",
        "artist": "SHANIA TWAIN",
        "tracks": [
            { "id": 1, "name": "Man! I Feel Like a Woman!", "artist": "SHANIA TWAIN", "duration": "3:53", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3" },
            { "id": 2, "name": "I'm Holdin' On to Love", "artist": "SHANIA TWAIN", "duration": "3:30", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3" },
            { "id": 3, "name": "Love Gets Me Every Time", "artist": "SHANIA TWAIN", "duration": "3:33", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3" }
        ]
    },
    {
        "id": "taylor-swift-1989-tv",
        "title": "1989 (TAYLOR'S VERSION)",
        "artist": "TAYLOR SWIFT",
        "tracks": [
            { "id": 1, "name": "Welcome to New York (Taylor's Version)", "artist": "TAYLOR SWIFT", "duration": "3:32", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" },
            { "id": 2, "name": "Blank Space (Taylor's Version)", "artist": "TAYLOR SWIFT", "duration": "3:51", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3" },
            { "id": 3, "name": "Style (Taylor's Version)", "artist": "TAYLOR SWIFT", "duration": "3:51", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3" }
        ]
    },
    {
        "id": "daft-punk-ram-10th",
        "title": "RANDOM ACCESS MEMORIES",
        "artist": "DAFT PUNK",
        "tracks": [
            { "id": 1, "name": "Give Life Back to Music", "artist": "DAFT PUNK", "duration": "4:35", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3" },
            { "id": 2, "name": "Giorgio by Moroder", "artist": "DAFT PUNK", "duration": "9:04", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-9.mp3" },
            { "id": 3, "name": "Get Lucky", "artist": "DAFT PUNK", "duration": "6:09", "previewUrl": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-12.mp3" }
        ]
    }
]

def _get_request_base_url(request: Request) -> str:
    """Xác định Base URL chính xác cho Stream (qua Proxy / Domain Public / Header)"""
    try:
        from Backend.helper.settings_manager import SettingsManager
        mgr_url = (SettingsManager.current().base_url or "").rstrip("/")
        if mgr_url and mgr_url.startswith("http"):
            return mgr_url
    except Exception:
        pass

    proto = request.headers.get("x-forwarded-proto") or request.headers.get("x-scheme") or request.url.scheme or "http"
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc
    return f"{proto}://{host}".rstrip("/")

def _safe_content_disposition(title: str, ext: str = ".m3u8") -> str:
    """Tạo Content-Disposition header an toàn, tương thích chuẩn ASCII và UTF-8 RFC 5987 (tránh lỗi latin-1 encoding)"""
    normalized = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
    clean_ascii = re.sub(r'[^a-zA-Z0-9_\-.]', '_', normalized).strip('_') or "playlist"
    ascii_fname = f"{clean_ascii}{ext}"

    clean_full = re.sub(r'[\\/:*?"<>|]', '_', title).strip() or "playlist"
    full_fname = f"{clean_full}{ext}"
    utf8_fname = quote(full_fname)

    return f'inline; filename="{ascii_fname}"; filename*=UTF-8\'\'{utf8_fname}'


def _build_m3u8_content(title: str, tracks: list, base_url: str) -> str:
    lines = ["#EXTM3U", "#EXTENC:UTF-8", f"#PLAYLIST:{title}\n"]
    for idx, t in enumerate(tracks):
        dur_str = str(t.get("duration", "0"))
        sec = -1
        if dur_str.isdigit():
            sec = int(dur_str)
        elif ":" in dur_str:
            parts = dur_str.split(":")
            if len(parts) == 2:
                sec = (int(parts[0]) if parts[0].isdigit() else 0) * 60 + (int(parts[1]) if parts[1].isdigit() else 0)
            elif len(parts) == 3:
                sec = (int(parts[0]) if parts[0].isdigit() else 0) * 3600 + (int(parts[1]) if parts[1].isdigit() else 0) * 60 + (int(parts[2]) if parts[2].isdigit() else 0)

        name = t.get("name") or t.get("title") or f"Track {idx + 1}"
        artist = t.get("artist") or "XTAPO Music"
        chat_id = t.get("chat_id") or t.get("chatId")
        msg_id = t.get("msg_id") or t.get("msgId")
        preview_url = t.get("previewUrl") or t.get("url") or ""

        if chat_id and msg_id:
            stream_url = f"{base_url}/api/music/stream/{chat_id}/{msg_id}"
        elif preview_url:
            if preview_url.startswith("/"):
                stream_url = f"{base_url}{preview_url}"
            else:
                stream_url = preview_url
        else:
            continue

        lines.append(f"#EXTINF:{sec},{artist} - {name}")
        lines.append(stream_url)
        lines.append("")
    return "\n".join(lines)


# ── Dynamic Playlist Share Endpoint (Đảm bảo 100% Client Sync với VLC/PotPlayer) ──

@router.post("/api/music/playlist/share")
async def create_shared_playlist(payload: dict, request: Request):
    """Tạo hoặc đồng bộ M3U8 Playlist tức thì từ danh sách bài hát của Frontend"""
    title = payload.get("title", "XTAPO_Playlist").strip() or "XTAPO_Playlist"
    tracks = payload.get("tracks", [])
    if not tracks:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Danh sách bài hát rỗng"})

    share_key = secrets.token_hex(8)
    _SHARED_M3U8_CACHE[share_key] = {
        "title": title,
        "tracks": tracks,
        "created_at": time.time()
    }

    base_url = _get_request_base_url(request)
    m3u8_url = f"{base_url}/api/music/playlist/share/{share_key}.m3u8"
    return {"status": "success", "share_id": share_key, "m3u8_url": m3u8_url}


@router.get("/api/music/playlist/share/{share_id:path}")
async def get_shared_playlist_m3u8(request: Request, share_id: str):
    """Trả về M3U8 từ bộ nhớ chia sẻ động"""
    base_url = _get_request_base_url(request)
    if share_id.endswith(".m3u8"):
        share_id = share_id[:-5]

    item = _SHARED_M3U8_CACHE.get(share_id)
    if not item:
        # Thử tìm trong DB nếu có lưu
        try:
            coll = db.dbs["tracking"]["music_shared_playlists"]
            doc = await coll.find_one({"_id": share_id})
            if doc:
                item = doc
        except Exception:
            pass

    if not item:
        raise HTTPException(status_code=404, detail="Playlist share link expired or not found")

    title = item.get("title", "Shared Playlist")
    tracks = item.get("tracks", [])
    m3u8_text = _build_m3u8_content(title, tracks, base_url)

    return PlainResponse(
        content=m3u8_text,
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition(title, ".m3u8"),
            "Cache-Control": "public, max-age=3600",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/api/music/playlist/album/{album_id:path}")
async def stream_album_m3u8(request: Request, album_id: str):
    """Trả về file playlist .m3u8 trực tiếp của Album, Thể Loại, Nghệ Sĩ hoặc Playlist"""
    base_url = _get_request_base_url(request)
    if album_id.endswith(".m3u8"):
        album_id = album_id[:-5]

    decoded_id = unquote(album_id).strip()
    raw_lower = decoded_id.lower()

    # 1. Nếu là Genre Playlist: genre-EDM/Remix hoặc genre/EDM/Remix
    if raw_lower.startswith("genre-") or raw_lower.startswith("genre/"):
        genre_name = decoded_id[6:] if raw_lower.startswith("genre-") else decoded_id[6:]
        return await stream_genre_m3u8(request, genre_name)

    # 2. Nếu là Artist Spotlight: artist-Shania Twain hoặc artist/Shania Twain
    if raw_lower.startswith("artist-") or raw_lower.startswith("artist/"):
        artist_name = decoded_id[7:] if raw_lower.startswith("artist-") else decoded_id[7:]
        return await stream_artist_m3u8(request, artist_name)

    # 3. Nếu là User Custom Playlist: pl-pl_123 hoặc pl_123
    if raw_lower.startswith("pl-") or raw_lower.startswith("playlist-"):
        pl_id = decoded_id[3:] if raw_lower.startswith("pl-") else decoded_id[9:]
        from Backend.fastapi.routes.music_auth import stream_user_playlist_m3u8
        return await stream_user_playlist_m3u8(request, pl_id)

    # 4. Tìm kiếm Album thông thường trong Database và Fallback
    data = await _db_load_library() or []
    all_albums = list(data) + DEMO_ALBUMS_FALLBACK
    target_album = None

    for alb in all_albums:
        curr_id = str(alb.get("id", "")).strip().lower()
        curr_title = str(alb.get("title", "")).strip().lower()
        if curr_id == raw_lower or curr_title == raw_lower:
            target_album = alb
            break

    # Nếu chưa thấy, thử tìm partial match
    if not target_album:
        for alb in all_albums:
            curr_title = str(alb.get("title", "")).strip().lower()
            if raw_lower in curr_title or curr_title in raw_lower:
                target_album = alb
                break

    # 5. Nếu vẫn không thấy, kiểm tra xem có phải là 1 Thể loại trong kho không
    if not target_album:
        genre_tracks = []
        for alb in all_albums:
            alb_artist = alb.get("artist", "")
            for t in alb.get("tracks", []):
                if not t.get("artist"):
                    t["artist"] = alb_artist
                track_genre = str(t.get("genre", "")).lower()
                if raw_lower in track_genre:
                    genre_tracks.append(t)
        if genre_tracks:
            m3u8_text = _build_m3u8_content(f"Genre_{decoded_id}", genre_tracks, base_url)
            return PlainResponse(
                content=m3u8_text,
                media_type="audio/x-mpegurl; charset=utf-8",
                headers={
                    "Content-Disposition": _safe_content_disposition(f"Genre_{decoded_id}", ".m3u8"),
                    "Cache-Control": "public, max-age=300",
                    "Access-Control-Allow-Origin": "*"
                }
            )

    if not target_album:
        raise HTTPException(status_code=404, detail=f"Album '{album_id}' not found")

    title = target_album.get("title", "Album")
    tracks = target_album.get("tracks", [])
    m3u8_text = _build_m3u8_content(title, tracks, base_url)

    return PlainResponse(
        content=m3u8_text,
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition(title, ".m3u8"),
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*"
        }
    )


_M3U8_MEM_CACHE: Dict[str, tuple[str, float]] = {}
_M3U8_MEM_CACHE_TTL = 300.0  # 5 phút

@router.get("/api/music/playlist/all.m3u8")
@router.get("/api/music/playlist/all")
async def stream_all_music_m3u8(request: Request):
    """Trả về file playlist .m3u8 toàn bộ kho nhạc thư viện (tự động cache RAM)"""
    base_url = _get_request_base_url(request)
    cache_key = f"all_{base_url}"
    now = time.time()

    if cache_key in _M3U8_MEM_CACHE:
        cached_text, cached_at = _M3U8_MEM_CACHE[cache_key]
        if now - cached_at < _M3U8_MEM_CACHE_TTL:
            return PlainResponse(
                content=cached_text,
                media_type="audio/x-mpegurl; charset=utf-8",
                headers={
                    "Content-Disposition": _safe_content_disposition("XTAPO_All_Music_Library", ".m3u8"),
                    "Cache-Control": "public, max-age=300",
                    "Access-Control-Allow-Origin": "*"
                }
            )

    data = await _db_load_library() or []
    all_albums = list(data) if data else DEMO_ALBUMS_FALLBACK

    all_tracks = []
    for alb in all_albums:
        for t in alb.get("tracks", []):
            if not t.get("artist"):
                t["artist"] = alb.get("artist", "")
            all_tracks.append(t)

    m3u8_text = _build_m3u8_content("XTAPO_All_Music_Library", all_tracks, base_url)
    _M3U8_MEM_CACHE[cache_key] = (m3u8_text, now)

    return PlainResponse(
        content=m3u8_text,
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition("XTAPO_All_Music_Library", ".m3u8"),
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/api/music/playlist/artist/{artist_name:path}")
async def stream_artist_m3u8(request: Request, artist_name: str):
    """Trả về playlist .m3u8 cho ca sĩ/nghệ sĩ cụ thể"""
    base_url = _get_request_base_url(request)
    if artist_name.endswith(".m3u8"):
        artist_name = artist_name[:-5]

    data = await _db_load_library() or []
    all_albums = list(data) + DEMO_ALBUMS_FALLBACK
    decoded_artist = unquote(artist_name).strip().lower()
    artist_tracks = []
    display_artist = unquote(artist_name).strip()

    for alb in all_albums:
        alb_artist = alb.get("artist", "")
        for t in alb.get("tracks", []):
            track_artist = t.get("artist") or alb_artist
            if decoded_artist in track_artist.lower() or track_artist.lower() in decoded_artist:
                display_artist = track_artist
                artist_tracks.append(t)

    if not artist_tracks:
        # Fallback lấy các bài hát khớp
        for alb in all_albums:
            for t in alb.get("tracks", []):
                if decoded_artist in t.get("name", "").lower():
                    artist_tracks.append(t)

    if not artist_tracks:
        raise HTTPException(status_code=404, detail=f"No tracks found for artist: {artist_name}")

    m3u8_text = _build_m3u8_content(f"Artist_{display_artist}", artist_tracks, base_url)
    return PlainResponse(
        content=m3u8_text,
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition(f"Artist_{display_artist}", ".m3u8"),
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*"
        }
    )


@router.get("/api/music/playlist/genre/{genre_name:path}")
async def stream_genre_m3u8(request: Request, genre_name: str):
    """Trả về playlist .m3u8 theo thể loại"""
    base_url = _get_request_base_url(request)
    if genre_name.endswith(".m3u8"):
        genre_name = genre_name[:-5]

    data = await _db_load_library() or []
    all_albums = list(data) + DEMO_ALBUMS_FALLBACK
    decoded_genre = unquote(genre_name).strip().lower()
    clean_genre_key = re.sub(r'[\/\-_ ]+', '', decoded_genre)
    genre_tracks = []
    display_genre = unquote(genre_name).strip()

    for alb in all_albums:
        alb_artist = alb.get("artist", "")
        for t in alb.get("tracks", []):
            if not t.get("artist"):
                t["artist"] = alb_artist
            track_genre = str(t.get("genre", "")).lower()
            clean_track_genre = re.sub(r'[\/\-_ ]+', '', track_genre)

            if (
                clean_genre_key in clean_track_genre 
                or clean_track_genre in clean_genre_key 
                or (decoded_genre in ["khác", "other"] and not track_genre)
            ):
                genre_tracks.append(t)

    if not genre_tracks:
        # Nếu chưa tìm thấy, quét tất cả bài hát và dùng detect_genre_from_track_info
        for alb in all_albums:
            for t in alb.get("tracks", []):
                det = detect_genre_from_track_info(t).lower()
                clean_det = re.sub(r'[\/\-_ ]+', '', det)
                if clean_genre_key in clean_det or clean_det in clean_genre_key:
                    genre_tracks.append(t)

    if not genre_tracks:
        raise HTTPException(status_code=404, detail=f"No tracks found for genre: {genre_name}")

    m3u8_text = _build_m3u8_content(f"Genre_{display_genre}", genre_tracks, base_url)
    return PlainResponse(
        content=m3u8_text,
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition(f"Genre_{display_genre}", ".m3u8"),
            "Cache-Control": "public, max-age=300",
            "Access-Control-Allow-Origin": "*"
        }
    )



def clear_playlist_cache() -> None:
    _M3U8_MEM_CACHE.clear()
