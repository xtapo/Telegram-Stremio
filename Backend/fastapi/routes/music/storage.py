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
    LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE, MUSIC_DATA_DIR, MUSIC_DIR,
)

CHANNELS_FILE = os.path.join(MUSIC_DATA_DIR, "music_channels.json")
LEGACY_CHANNELS_FILE = os.path.join(MUSIC_DIR, "music_channels.json")


# ── MongoDB & JSON Dual-Storage Helpers ──────────────────────────────────────
def _load_channels_file() -> list:
    for path in [CHANNELS_FILE, LEGACY_CHANNELS_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                LOGGER.error(f"[MUSIC] Error reading channels file {path}: {e}")
    return []


def _save_channels_file(channels: list):
    for path in [CHANNELS_FILE, LEGACY_CHANNELS_FILE]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(channels, f, ensure_ascii=False, indent=2)
        except Exception as e:
            LOGGER.error(f"[MUSIC] Error saving channels file to {path}: {e}")


_IN_MEMORY_CHANNELS_CACHE = None

async def _db_load_channels() -> list:
    global _IN_MEMORY_CHANNELS_CACHE
    if _IN_MEMORY_CHANNELS_CACHE is not None:
        return _IN_MEMORY_CHANNELS_CACHE

    # 1. Đọc từ file cache cục bộ trước để phản hồi tức thì (< 1ms)
    local_channels = _load_channels_file()
    if local_channels:
        for item in local_channels:
            item["last_scanned_id"] = int(item.get("last_scanned_id", 0) or 0)
            item["last_scanned_at"] = str(item.get("last_scanned_at", "") or "")
            item["total_tracks"] = int(item.get("total_tracks", 0) or 0)
            item["auto_sync"] = bool(item.get("auto_sync", False))
        _IN_MEMORY_CHANNELS_CACHE = local_channels
        return local_channels

    # 2. Nếu chưa có file cache: đọc từ MongoDB
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            cursor = db.dbs["tracking"]["music_channels"].find()
            docs = [d async for d in cursor]
            if docs:
                channels = [
                    {
                        "id": str(d.get("id") or d.get("_id")),
                        "name": d.get("name", ""),
                        "username": d.get("username", ""),
                        "last_scanned_id": int(d.get("last_scanned_id", 0) or 0),
                        "last_scanned_at": str(d.get("last_scanned_at", "") or ""),
                        "total_tracks": int(d.get("total_tracks", 0) or 0),
                        "auto_sync": bool(d.get("auto_sync", False)),
                    }
                    for d in docs
                ]
                _IN_MEMORY_CHANNELS_CACHE = channels
                _save_channels_file(channels)
                return channels
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not read channels from MongoDB: {e}")
    return []


async def _db_save_channels(channels: list):
    global _IN_MEMORY_CHANNELS_CACHE
    _IN_MEMORY_CHANNELS_CACHE = channels
    _save_channels_file(channels)
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            coll = db.dbs["tracking"]["music_channels"]
            curr_ids = [str(c.get("id")) for c in channels]
            if curr_ids:
                await coll.delete_many({"_id": {"$nin": curr_ids}})
                for c in channels:
                    ch_id = str(c.get("id"))
                    doc = {
                        "id": ch_id,
                        "name": c.get("name", ""),
                        "username": c.get("username", ""),
                        "last_scanned_id": int(c.get("last_scanned_id", 0) or 0),
                        "last_scanned_at": str(c.get("last_scanned_at", "") or ""),
                        "total_tracks": int(c.get("total_tracks", 0) or 0),
                        "auto_sync": bool(c.get("auto_sync", False)),
                    }
                    await coll.update_one(
                        {"_id": ch_id},
                        {"$set": doc},
                        upsert=True
                    )
            else:
                await coll.delete_many({})
            LOGGER.info(f"[MUSIC DB] Đã đồng bộ {len(channels)} kênh lên MongoDB.")
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not save channels to MongoDB: {e}")


async def _db_update_channel_progress(chat_id: str, last_scanned_id: int, last_scanned_at: str = "", total_tracks: int = 0):
    global _IN_MEMORY_CHANNELS_CACHE

    # Trong lúc scan, cache này đã được nạp sẵn. Dùng trực tiếp để tránh gọi
    # lại lớp load/cache ở mỗi checkpoint; chỉ fallback khi chưa có cache.
    channels = _IN_MEMORY_CHANNELS_CACHE
    if channels is None:
        channels = await _db_load_channels()
    target_str = str(chat_id)
    updated = False
    now_str = last_scanned_at or time.strftime("%H:%M %d/%m/%Y")

    for ch in channels:
        if str(ch.get("id")) == target_str:
            curr_last = int(ch.get("last_scanned_id", 0) or 0)
            if last_scanned_id > curr_last:
                ch["last_scanned_id"] = int(last_scanned_id)
                ch["last_scanned_at"] = now_str
                updated = True
            if total_tracks > 0:
                ch["total_tracks"] = int(total_tracks)
                updated = True
            break

    if updated:
        _save_channels_file(channels)
        try:
            if db and hasattr(db, "dbs") and "tracking" in db.dbs:
                coll = db.dbs["tracking"]["music_channels"]
                update_fields = {"last_scanned_id": int(last_scanned_id), "last_scanned_at": now_str}
                if total_tracks > 0:
                    update_fields["total_tracks"] = int(total_tracks)
                await coll.update_one(
                    {"_id": target_str},
                    {"$set": update_fields}
                )
        except Exception as e:
            LOGGER.warning(f"[MUSIC DB] Could not update channel progress: {e}")


_IN_MEMORY_LIBRARY_CACHE = None
_LIBRARY_BG_REFRESH_LOCK = asyncio.Lock()
_LIBRARY_MIGRATED = False  # Flag để chỉ migrate 1 lần
_LIBRARY_BG_SAVE_TASKS = set()

# ── Collection mới: mỗi album = 1 document trong `music_albums` ──

def _get_albums_collection():
    """Lấy collection music_albums từ tracking DB."""
    if db and hasattr(db, "dbs") and "tracking" in db.dbs:
        return db.dbs["tracking"]["music_albums"]
    return None

def _get_legacy_collection():
    """Lấy collection cũ music_library (single-document schema)."""
    if db and hasattr(db, "dbs") and "tracking" in db.dbs:
        return db.dbs["tracking"]["music_library"]
    return None

def _serialize_albums_json(albums: list) -> bytes:
    """Serialize thư viện một lần để tái sử dụng cho cache/gzip."""
    return json.dumps(albums, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _compress_albums(albums: list) -> bytes:
    """Nén thư viện với mức CPU thấp để không làm nghẽn máy khi scan kết thúc."""
    try:
        level = max(1, min(6, int(os.environ.get("MUSIC_LIBRARY_GZIP_LEVEL", "1"))))
    except (TypeError, ValueError):
        level = 1
    return gzip.compress(_serialize_albums_json(albums), compresslevel=level)


def _write_library_cache_files(albums: list) -> None:
    """Ghi cache JSON ngoài event loop, chỉ serialize một lần cho cả hai path."""
    payload = _serialize_albums_json(albums)
    for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp_path = f"{path}.tmp"
            with open(tmp_path, "wb") as f:
                f.write(payload)
            os.replace(tmp_path, path)
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to write cache to {path}: {e}")

def _decompress_albums(compressed: bytes) -> list:
    """Giải nén gzip binary thành danh sách albums gốc trong RAM."""
    raw_bytes = gzip.decompress(compressed)
    return json.loads(raw_bytes.decode("utf-8"))

def generate_album_id(title: str, artist: str = "", year: str = "") -> str:
    """Tạo ID album duy nhất, không trùng lặp, hỗ trợ đầy đủ tiếng Việt và ký tự đặc biệt."""
    clean_title = re.sub(r'[^a-zA-Z0-9_-]', '-', (title or 'album').lower().strip())
    clean_title = re.sub(r'-+', '-', clean_title).strip('-')[:35]
    clean_artist = re.sub(r'[^a-zA-Z0-9_-]', '-', (artist or 'artist').lower().strip())[:15]
    h = hashlib.md5(f"{title}::{artist}::{year}".encode("utf-8")).hexdigest()[:8]
    return f"tg-{clean_title or 'album'}-{clean_artist or 'artist'}-{h}"


async def _save_compressed_mongo_library(albums: list, force: bool = False):
    """Lưu bản nén Gzip lên MongoDB (giảm 20MB xuống ~1.5MB, đọc trong 1 giây) có cơ chế bảo vệ dữ liệu."""
    coll_lib = _get_legacy_collection()
    if coll_lib is None or not albums:
        return
    try:
        # Kiểm tra an toàn: Tuyệt đối không tự động ghi đè thư viện lớn bằng thư viện nhỏ (chống race condition mất dữ liệu)
        if not force:
            try:
                existing = await asyncio.wait_for(
                    coll_lib.find_one({"_id": "telegram_music_library_gz"}, projection={"album_count": 1, "count": 1}),
                    timeout=8.0
                )
                if existing:
                    existing_count = existing.get("album_count", 0)
                    if existing_count > 0 and len(albums) < existing_count * 0.7:
                        LOGGER.error(
                            f"[MUSIC DB] ⛔ CHẶN GHI ĐÈ GZIP: Số album mới ({len(albums)}) < 70% số album hiện có trên MongoDB ({existing_count}). "
                            f"Hủy tự động ghi đè để ngăn chặn mất dữ liệu!"
                        )
                        return
            except Exception as e:
                LOGGER.warning(f"[MUSIC DB] Không thể kiểm tra album_count hiện tại: {e}")

        compressed_bytes = await asyncio.to_thread(_compress_albums, albums)
        total_tracks = sum(len(a.get("tracks", [])) for a in albums)
        doc_payload = {
            "compressed_data": compressed_bytes,
            "count": total_tracks,
            "album_count": len(albums),
            "compressed_size_kb": round(len(compressed_bytes) / 1024, 1),
            "updated_at": time.time()
        }
        await coll_lib.update_one(
            {"_id": "telegram_music_library_gz"},
            {"$set": doc_payload},
            upsert=True
        )
        LOGGER.info(f"[MUSIC DB] Đã lưu bản nén Gzip lên MongoDB: {len(albums)} albums, {total_tracks} bài ({len(compressed_bytes)/1024:.1f} KB).")

        # Lưu thêm bản backup dự phòng nếu thư viện >= 100 albums
        if len(albums) >= 100:
            await coll_lib.update_one(
                {"_id": "telegram_music_library_gz_backup"},
                {"$set": doc_payload},
                upsert=True
            )
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Lỗi lưu bản nén Gzip lên MongoDB: {e}")


async def _ensure_gz_if_missing(albums: list):
    """Chỉ lưu bản nén Gzip nếu trên MongoDB hoàn toàn chưa có hoặc số album mới nhiều hơn."""
    coll_lib = _get_legacy_collection()
    if coll_lib is None or not albums:
        return
    try:
        existing = await coll_lib.find_one({"_id": "telegram_music_library_gz"}, projection={"album_count": 1})
        if not existing or existing.get("album_count", 0) < len(albums):
            await _save_compressed_mongo_library(albums, force=False)
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] _ensure_gz_if_missing failed: {e}")

async def _migrate_legacy_to_per_album() -> list | None:
    """
    One-time migration: đọc document cũ (telegram_music_library) 
    và tách thành per-album documents trong music_albums collection.
    Trả về list albums nếu migration thành công (để populate cache ngay).
    """
    global _LIBRARY_MIGRATED, _IN_MEMORY_LIBRARY_CACHE
    if _LIBRARY_MIGRATED:
        return None
    _LIBRARY_MIGRATED = True

    coll_new = _get_albums_collection()
    coll_old = _get_legacy_collection()
    if coll_new is None or coll_old is None:
        return None

    # Kiểm tra xem collection mới đã có data chưa
    try:
        existing_count = await asyncio.wait_for(coll_new.count_documents({}), timeout=10.0)
        if existing_count > 0:
            LOGGER.info(f"[MUSIC DB] Migration skipped: music_albums already has {existing_count} documents.")
            return None
    except Exception:
        return None

    try:
        LOGGER.info("[MUSIC DB] Starting migration from single-document to per-album schema...")
        doc = await asyncio.wait_for(
            coll_old.find_one(
                {"_id": "telegram_music_library"},
                projection={"albums": 1, "_id": 0}
            ),
            timeout=180.0
        )
        if not doc or "albums" not in doc or not isinstance(doc["albums"], list):
            LOGGER.info("[MUSIC DB] Migration: no legacy data found.")
            return None

        albums = doc["albums"]
        if not albums:
            return None

        # Tự động nén và lưu bản Gzip ngay
        asyncio.create_task(_save_compressed_mongo_library(albums))

        # Insert từng album vào collection mới
        docs_to_insert = []
        for alb in albums:
            album_id = alb.get("id", "")
            if not album_id:
                title = alb.get("title", "unknown")
                artist = alb.get("artist", "unknown")
                album_id = f"{title}-{artist}".lower().replace(" ", "-")
                alb["id"] = album_id
            album_doc = {**alb, "_id": album_id}
            docs_to_insert.append(album_doc)

        if docs_to_insert:
            for i in range(0, len(docs_to_insert), 50):
                batch = docs_to_insert[i:i+50]
                try:
                    await coll_new.insert_many(batch, ordered=False)
                except Exception as e:
                    if "duplicate" not in str(e).lower() and "E11000" not in str(e):
                        LOGGER.warning(f"[MUSIC DB] Migration batch insert warning: {e}")

            LOGGER.info(f"[MUSIC DB] Migration completed: {len(docs_to_insert)} albums migrated to per-album schema.")

        # Ghi thẳng vào cache luôn
        _IN_MEMORY_LIBRARY_CACHE = albums
        for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(albums, f, ensure_ascii=False)
            except Exception:
                pass
        LOGGER.info(f"[MUSIC DB] Migration: cached {len(albums)} albums to memory + file.")

        return albums
    except asyncio.TimeoutError:
        LOGGER.warning("[MUSIC DB] Migration: timeout reading legacy document (180s). Will retry next restart.")
        _LIBRARY_MIGRATED = False
        return None
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Migration error: {e}")
        _LIBRARY_MIGRATED = False
        return None

async def _db_fetch_library_from_mongo() -> list | None:
    """
    Fetch library từ MongoDB theo thứ tự ưu tiên:
    1. Bản nén Gzip (telegram_music_library_gz) ~1.5MB, tải chỉ 1-2s (có retry khi container cold boot).
    1b. Bản dự phòng Gzip (telegram_music_library_gz_backup).
    2. Per-album collection (music_albums).
    3. Legacy single-document (telegram_music_library).
    """
    coll_lib = _get_legacy_collection()

    # ── Ưu tiên 1: Đọc bản nén Gzip chính (thử 2 lần để xử lý độ trễ cold start của Docker) ──
    if coll_lib is not None:
        for attempt in range(2):
            try:
                doc_gz = await asyncio.wait_for(
                    coll_lib.find_one({"_id": "telegram_music_library_gz"}),
                    timeout=35.0 if attempt == 0 else 45.0
                )
                if doc_gz and "compressed_data" in doc_gz and doc_gz["compressed_data"]:
                    c_bytes = doc_gz["compressed_data"]
                    albums = _decompress_albums(c_bytes)
                    if albums and isinstance(albums, list) and len(albums) > 0:
                        LOGGER.info(f"[MUSIC DB] ⚡ Tải thành công {len(albums)} albums từ bản nén Gzip trên MongoDB ({len(c_bytes)/1024:.1f} KB)!")
                        return albums
                break
            except asyncio.TimeoutError:
                LOGGER.warning(f"[MUSIC DB] Gzip đọc timeout (thử {attempt+1}/2). Đang chờ kết nối MongoDB hoàn tất...")
                await asyncio.sleep(2.0)
            except Exception as e:
                LOGGER.info(f"[MUSIC DB] Gzip document chưa sẵn sàng: {e}")
                break

        # ── Ưu tiên 1b: Đọc bản dự phòng Gzip nếu bản chính gặp sự cố ──
        try:
            doc_bak = await asyncio.wait_for(
                coll_lib.find_one({"_id": "telegram_music_library_gz_backup"}),
                timeout=25.0
            )
            if doc_bak and "compressed_data" in doc_bak and doc_bak["compressed_data"]:
                c_bytes = doc_bak["compressed_data"]
                albums = _decompress_albums(c_bytes)
                if albums and isinstance(albums, list) and len(albums) > 0:
                    LOGGER.info(f"[MUSIC DB] ⚡ Phục hồi thành công {len(albums)} albums từ bản dự phòng Gzip trên MongoDB ({len(c_bytes)/1024:.1f} KB)!")
                    asyncio.create_task(_save_compressed_mongo_library(albums, force=True))
                    return albums
        except Exception:
            pass

    # ── Ưu tiên 2: Đọc từ per-album collection (music_albums) ──
    coll = _get_albums_collection()
    if coll is not None:
        try:
            count = await asyncio.wait_for(coll.count_documents({}), timeout=30.0)
            if count > 0:
                LOGGER.info(f"[MUSIC DB] Đang nạp {count} albums từ per-album collection...")
                albums = []
                cursor = coll.find({}, projection={"_id": 0}).batch_size(300)
                async for doc in cursor:
                    albums.append(doc)
                    if len(albums) % 1000 == 0:
                        LOGGER.info(f"[MUSIC DB] ...đã đọc {len(albums)}/{count} albums")
                if albums:
                    LOGGER.info(f"[MUSIC DB] Đã nạp {len(albums)} albums từ per-album collection.")
                    asyncio.create_task(_ensure_gz_if_missing(albums))
                    return albums
        except Exception as e:
            LOGGER.warning(f"[MUSIC DB] Per-album read failed: {e}")

    # ── Ưu tiên 3: Đọc từ legacy single-document (telegram_music_library) ──
    if coll_lib is not None:
        try:
            LOGGER.info("[MUSIC DB] Đang đọc từ legacy single-document schema...")
            doc = await asyncio.wait_for(
                coll_lib.find_one(
                    {"_id": "telegram_music_library"},
                    projection={"albums": 1, "_id": 0}
                ),
                timeout=60.0
            )
            if doc and "albums" in doc and isinstance(doc["albums"], list) and doc["albums"]:
                albums = doc["albums"]
                LOGGER.info(f"[MUSIC DB] Đã nạp {len(albums)} albums từ legacy schema.")
                asyncio.create_task(_ensure_gz_if_missing(albums))
                return albums
        except Exception as e:
            LOGGER.warning(f"[MUSIC DB] Legacy read failed: {e}")

    return None


_PRELOAD_STARTED = False

async def _startup_preload_library():
    """
    Background task: preload library data khi server khởi động.
    """
    global _IN_MEMORY_LIBRARY_CACHE, _PRELOAD_STARTED
    if _PRELOAD_STARTED and _IN_MEMORY_LIBRARY_CACHE is not None:
        return
    _PRELOAD_STARTED = True

    # 1. Kiểm tra file cache trước
    for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        _IN_MEMORY_LIBRARY_CACHE = data
                        LOGGER.info(f"[MUSIC DB] Startup preload: loaded {len(data)} albums from file cache ({path}).")
                        asyncio.create_task(_preload_artists_cache_bg())
                        return
            except Exception:
                pass

    # 2. Không có file cache → tải từ MongoDB
    LOGGER.info("[MUSIC DB] Startup preload: no file cache found. Loading from MongoDB...")
    try:
        albums = await _db_fetch_library_from_mongo()
        if albums:
            _IN_MEMORY_LIBRARY_CACHE = albums
            for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(albums, f, ensure_ascii=False)
                except Exception:
                    pass
            LOGGER.info(f"[MUSIC DB] Startup preload: successfully cached {len(albums)} albums.")
            asyncio.create_task(_preload_artists_cache_bg())
        else:
            LOGGER.warning("[MUSIC DB] Startup preload: no data returned from MongoDB.")
    except Exception as e:
        LOGGER.error(f"[MUSIC DB] Startup preload failed: {e}")
        _PRELOAD_STARTED = False


async def _preload_artists_cache_bg():
    """Tải trước danh sách ca sĩ vào RAM & SSD ngay khi khởi động để phản hồi < 1ms."""
    try:
        from Backend.fastapi.routes.music.catalog import get_all_artists
        await get_all_artists(force_refresh=False)
        LOGGER.info("[MUSIC DB] Artists cache successfully preloaded.")
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Preload artists cache background failed: {e}")


async def _bg_refresh_library_from_mongo():
    """Background task: fetch from MongoDB and update cache without blocking user requests."""
    global _IN_MEMORY_LIBRARY_CACHE
    if _LIBRARY_BG_REFRESH_LOCK.locked():
        return
    async with _LIBRARY_BG_REFRESH_LOCK:
        try:
            LOGGER.info("[MUSIC DB] Background refresh: fetching library from MongoDB...")
            albums = await _db_fetch_library_from_mongo()
            if albums:
                # Bảo vệ an toàn: Không ghi đè bộ nhớ nếu số album mới nạp ít hơn đáng kể so với cache hiện tại
                if _IN_MEMORY_LIBRARY_CACHE and len(_IN_MEMORY_LIBRARY_CACHE) > 0 and len(albums) < len(_IN_MEMORY_LIBRARY_CACHE) * 0.7:
                    LOGGER.warning(
                        f"[MUSIC DB] Background refresh: Bỏ qua ghi đè vì số album trả về ({len(albums)}) < 70% số album đang có trong cache RAM ({len(_IN_MEMORY_LIBRARY_CACHE)})."
                    )
                    return
                _IN_MEMORY_LIBRARY_CACHE = albums
                for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            json.dump(albums, f, ensure_ascii=False)
                    except Exception:
                        pass
                LOGGER.info(f"[MUSIC DB] Background refresh: updated cache with {len(albums)} albums.")
            else:
                LOGGER.warning("[MUSIC DB] Background refresh: MongoDB returned no data.")
        except Exception as e:
            LOGGER.error(f"[MUSIC DB] Background refresh failed: {e}")


async def _db_load_library(force_reload: bool = False) -> list:
    global _IN_MEMORY_LIBRARY_CACHE
    if not force_reload and _IN_MEMORY_LIBRARY_CACHE is not None:
        return _IN_MEMORY_LIBRARY_CACHE

    # 1. Đọc từ file cache cục bộ trước để phản hồi tức thì (< 5ms)
    for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        _IN_MEMORY_LIBRARY_CACHE = data
                        asyncio.create_task(_bg_refresh_library_from_mongo())
                        return data
            except Exception as e:
                LOGGER.error(f"[MUSIC] Failed to load library cache file from {path}: {e}")

    # 2. Không có file cache: Thử fetch nhanh bản Gzip từ MongoDB (chỉ mất ~1s)
    try:
        albums = await asyncio.wait_for(_db_fetch_library_from_mongo(), timeout=45.0)
        if albums:
            _IN_MEMORY_LIBRARY_CACHE = albums
            for path in [LIBRARY_CACHE_FILE, LEGACY_LIBRARY_CACHE_FILE]:
                try:
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(albums, f, ensure_ascii=False)
                except Exception:
                    pass
            return albums
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Fast MongoDB fetch not ready yet: {e}")

    # 3. Fallback: Kích hoạt preload nền và tạm thời trả về []
    asyncio.create_task(_startup_preload_library())
    return []


async def _db_save_library(
    albums: list,
    *,
    wait_remote: bool = True,
    sync_remote: bool = True,
    remote_album_ids: set[str] | None = None,
):
    global _IN_MEMORY_LIBRARY_CACHE
    _IN_MEMORY_LIBRARY_CACHE = albums
    try:
        from Backend.fastapi.routes.music.catalog import invalidate_artists_cache
        invalidate_artists_cache()
    except Exception:
        pass
    try:
        from Backend.fastapi.routes.music.playlists import clear_playlist_cache
        clear_playlist_cache()
    except Exception:
        pass

    # 1. Ghi file cache cục bộ ngoài event loop. Thư viện lớn trước đây bị
    # json.dump() hai lần ngay trong FastAPI nên có thể làm server đứng hình.
    await asyncio.to_thread(_write_library_cache_files, albums)

    if not sync_remote:
        return

    async def _sync_remote_library():
        # 2. Lưu bản nén Gzip lên MongoDB (nhanh nhất & nhẹ nhất)
        await _save_compressed_mongo_library(albums, force=True)

        # 3. Lưu theo per-album schema mới. Khi remote_album_ids được truyền vào
        # (scan append), chỉ thay các album thực sự bị ảnh hưởng thay vì xóa và
        # ghi lại toàn bộ hàng chục nghìn document.
        coll = _get_albums_collection()
        if coll is not None:
            try:
                albums_to_write = albums
                if remote_album_ids is None:
                    await coll.delete_many({})
                else:
                    albums_to_write = [
                        alb for alb in albums
                        if (alb.get("id") or "").strip() in remote_album_ids
                    ]
                    if remote_album_ids:
                        await coll.delete_many({"_id": {"$in": list(remote_album_ids)}})

                if albums_to_write:
                    seen_ids = set()
                    batch = []
                    for idx, alb in enumerate(albums_to_write):
                        album_id = (alb.get("id") or "").strip()
                        if not album_id:
                            title = alb.get("title", "unknown")
                            artist = alb.get("artist", "unknown")
                            album_id = generate_album_id(title, artist)
                            alb["id"] = album_id

                        # Bảo đảm 100% _id không bị trùng lặp trong MongoDB để không bao giờ bị mất album
                        if album_id in seen_ids:
                            album_id = f"{album_id}-{hashlib.md5(f'{album_id}_{idx}'.encode('utf-8')).hexdigest()[:6]}"
                            alb["id"] = album_id
                        seen_ids.add(album_id)

                        batch.append({**alb, "_id": album_id})
                        if len(batch) < 1000:
                            continue
                        try:
                            await coll.insert_many(batch, ordered=False)
                        except Exception as e:
                            if "duplicate" not in str(e).lower() and "E11000" not in str(e):
                                LOGGER.warning(f"[MUSIC DB] Save batch warning: {e}")
                        batch = []

                    if batch:
                        try:
                            await coll.insert_many(batch, ordered=False)
                        except Exception as e:
                            if "duplicate" not in str(e).lower() and "E11000" not in str(e):
                                LOGGER.warning(f"[MUSIC DB] Save batch warning: {e}")

                if remote_album_ids is None:
                    LOGGER.info(f"[MUSIC DB] Đã lưu {len(albums_to_write)} albums (per-album schema).")
                else:
                    LOGGER.info(
                        f"[MUSIC DB] Đã cập nhật {len(albums_to_write)} albums thay đổi "
                        f"trên per-album schema."
                    )
            except Exception as e:
                LOGGER.warning(f"[MUSIC DB] Could not save to per-album collection: {e}")

        # 4. Legacy single-document rất nặng với thư viện lớn vì PyMongo phải
        # BSON-encode toàn bộ albums thêm một lần. App hiện đọc Gzip/per-album
        # trước, nên chỉ ghi legacy khi người vận hành chủ động bật lại.
        coll_old = _get_legacy_collection()
        write_legacy = os.environ.get("MUSIC_WRITE_LEGACY_LIBRARY", "0").strip().lower() in {
            "1", "true", "yes", "on"
        }
        if coll_old is not None and write_legacy:
            try:
                await coll_old.update_one(
                    {"_id": "telegram_music_library"},
                    {"$set": {
                        "albums": albums,
                        "count": sum(len(a.get("tracks", [])) for a in albums),
                        "updated_at": time.time()
                    }},
                    upsert=True
                )
            except Exception as e:
                LOGGER.warning(f"[MUSIC DB] Could not sync to legacy collection: {e}")

    if wait_remote:
        await _sync_remote_library()
        return

    # Nút Shazam thủ công chỉ cần chờ cache RAM/file được ghi xong. MongoDB được
    # đồng bộ nền để một kết nối chậm không giữ trạng thái "Đang nhận diện" nhiều phút.
    task = asyncio.create_task(_sync_remote_library())
    _LIBRARY_BG_SAVE_TASKS.add(task)
    task.add_done_callback(_LIBRARY_BG_SAVE_TASKS.discard)
    LOGGER.info("[MUSIC DB] Đã ghi cache cục bộ; đang đồng bộ MongoDB ở nền.")




