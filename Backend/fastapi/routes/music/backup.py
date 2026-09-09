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

from Backend.fastapi.routes.music.common import MUSIC_DATA_DIR
from Backend.fastapi.routes.music.storage import (
    _db_load_channels, _db_load_library, _db_save_channels, _db_save_library,
)
from Backend.fastapi.routes.music.playlists import (
    _load_playlists_file, _save_playlists_file, clear_playlist_cache,
)
from Backend.fastapi.routes.music.catalog import invalidate_artists_cache

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ==============================================================================
# 11. MUSIC DATABASE BACKUP & RESTORE API
# ==============================================================================

BACKUP_DIR = os.path.join(MUSIC_DATA_DIR, "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

def _bson_to_json_safe(obj):
    """Chuyển đổi các kiểu dữ liệu đặc biệt của MongoDB (ObjectId, datetime, ...) sang dạng JSON-safe."""
    if isinstance(obj, dict):
        return {k: _bson_to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_bson_to_json_safe(x) for x in obj]
    from bson import ObjectId
    if isinstance(obj, ObjectId):
        return str(obj)
    from datetime import datetime, date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    return obj


async def _build_music_backup_data() -> dict:
    """Thu thập toàn bộ dữ liệu Music phục vụ sao lưu."""
    albums = await _db_load_library() or []
    channels = await _db_load_channels() or []
    playlists = _load_playlists_file() or []
    
    artists_metadata = []
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            coll = db.dbs["tracking"]["music_artists"]
            cursor = coll.find()
            async for doc in cursor:
                artists_metadata.append(doc)
    except Exception as e:
        LOGGER.warning(f"[BACKUP] Lỗi thu thập metadata ca sĩ: {e}")

    total_tracks = sum(len(a.get("tracks", [])) for a in albums if isinstance(a, dict))
    from datetime import datetime
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    data = {
        "app": "Telegram-Stremio-Music",
        "version": "1.0",
        "timestamp": time.time(),
        "created_at": now_str,
        "albums": albums,
        "channels": channels,
        "playlists": playlists,
        "artists_metadata": artists_metadata,
        "stats": {
            "albums_count": len(albums),
            "tracks_count": total_tracks,
            "channels_count": len(channels),
            "playlists_count": len(playlists),
            "artists_count": len(artists_metadata)
        }
    }
    return _bson_to_json_safe(data)

async def _perform_music_restore(backup_data: Any) -> dict:
    """Thực thi khôi phục dữ liệu từ từ điển hoặc danh sách sao lưu vào MongoDB + SSD + RAM."""
    albums = None
    channels = None
    playlists = None
    artists_metadata = None

    if isinstance(backup_data, list):
        # Người dùng tải lên trực tiếp file telegram_library.json hoặc mảng danh sách
        if backup_data and isinstance(backup_data[0], dict):
            sample = backup_data[0]
            if "last_scanned_id" in sample or ("username" in sample and "tracks" not in sample):
                channels = backup_data
            elif "playlist_id" in sample or ("tracks" in sample and "artist" not in sample and "title" in sample):
                first_track = sample.get("tracks", [{}])[0] if isinstance(sample.get("tracks"), list) and sample.get("tracks") else {}
                if "chat_id" in first_track or "file_id" in first_track or "artist" in sample:
                    albums = backup_data
                else:
                    playlists = backup_data
            else:
                albums = backup_data
        else:
            albums = backup_data

    elif isinstance(backup_data, dict):
        # Hỗ trợ trường hợp dữ liệu bọc trong {"data": ...}
        raw_data = backup_data.get("data") if isinstance(backup_data.get("data"), (dict, list)) else backup_data
        if isinstance(raw_data, list):
            albums = raw_data
        elif isinstance(raw_data, dict):
            albums = raw_data.get("albums") or raw_data.get("library") or raw_data.get("music_library")
            channels = raw_data.get("channels") or raw_data.get("music_channels")
            playlists = raw_data.get("playlists") or raw_data.get("telegram_playlists")
            artists_metadata = raw_data.get("artists_metadata") or raw_data.get("music_artists") or raw_data.get("artists")
    else:
        raise ValueError("Định dạng file không hợp lệ (phải là JSON Object hoặc Array).")

    # Nếu albums lưu dưới dạng dictionary {album_id: {...}}, chuẩn hóa thành list
    if isinstance(albums, dict):
        albums = list(albums.values())

    if albums is None and channels is None and playlists is None and artists_metadata is None:
        raise ValueError("File sao lưu không chứa dữ liệu hợp lệ (không tìm thấy kho nhạc, kênh hoặc danh sách phát).")

    restored_stats = {}

    # 1. Khôi phục Albums & Bài hát
    if albums is not None and isinstance(albums, list):
        await _db_save_library(albums)
        restored_stats["albums"] = len(albums)
        restored_stats["tracks"] = sum(len(a.get("tracks", [])) for a in albums if isinstance(a, dict))
        LOGGER.info(f"[RESTORE] Đã khôi phục thành công {restored_stats['albums']} albums ({restored_stats['tracks']} bài hát).")

    # 2. Khôi phục Channels
    if channels is not None and isinstance(channels, list):
        await _db_save_channels(channels)
        restored_stats["channels"] = len(channels)
        LOGGER.info(f"[RESTORE] Đã khôi phục thành công {len(channels)} kênh.")

    # 3. Khôi phục Playlists
    if playlists is not None and isinstance(playlists, list):
        _save_playlists_file(playlists)
        restored_stats["playlists"] = len(playlists)
        LOGGER.info(f"[RESTORE] Đã khôi phục thành công {len(playlists)} playlists.")

    # 4. Khôi phục Artists Metadata
    if artists_metadata is not None and isinstance(artists_metadata, list) and artists_metadata:
        try:
            if db and hasattr(db, "dbs") and "tracking" in db.dbs:
                coll = db.dbs["tracking"]["music_artists"]
                count = 0
                for art in artists_metadata:
                    if not isinstance(art, dict):
                        continue
                    art_id = str(art.get("_id") or (art.get("name", "").lower().strip() if art.get("name") else "")).strip()
                    if art_id:
                        # QUAN TRỌNG: Loại bỏ _id khỏi $set để MongoDB không ném lỗi immutable field
                        clean_art = {k: v for k, v in art.items() if k != "_id"}
                        if clean_art:
                            await coll.update_one({"_id": art_id}, {"$set": clean_art}, upsert=True)
                            count += 1
                restored_stats["artists"] = count
                LOGGER.info(f"[RESTORE] Đã khôi phục thành công {count} ca sĩ metadata.")
        except Exception as e:
            LOGGER.warning(f"[RESTORE] Lỗi phục hồi artists: {e}")

    invalidate_artists_cache()
    clear_playlist_cache()

    return restored_stats


@router.get("/api/music/backup/download")
async def download_music_backup(format: str = "gz", _: bool = Depends(require_auth)):
    """Tải trực tiếp file sao lưu toàn bộ Database nhạc về máy tính (.json.gz hoặc .json)"""
    try:
        backup_data = await _build_music_backup_data()
        from datetime import datetime
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        json_str = json.dumps(backup_data, ensure_ascii=False, indent=2)
        
        if format == "json":
            filename = f"music_backup_{ts_str}.json"
            return PlainResponse(
                content=json_str.encode("utf-8"),
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        else:
            filename = f"music_backup_{ts_str}.json.gz"
            gz_bytes = gzip.compress(json_str.encode("utf-8"), compresslevel=6)
            return PlainResponse(
                content=gz_bytes,
                media_type="application/gzip",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
    except Exception as e:
        LOGGER.error(f"[BACKUP DOWNLOAD] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/backup/create-snapshot")
async def create_backup_snapshot(_: bool = Depends(require_auth)):
    """Tạo một bản sao lưu lưu trữ trên ổ đĩa máy chủ (Music/data/backups)"""
    try:
        backup_data = await _build_music_backup_data()
        from datetime import datetime
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{ts_str}.json.gz"
        filepath = os.path.join(BACKUP_DIR, filename)

        json_str = json.dumps(backup_data, ensure_ascii=False)
        gz_bytes = gzip.compress(json_str.encode("utf-8"), compresslevel=6)

        with open(filepath, "wb") as f:
            f.write(gz_bytes)

        file_size_kb = round(len(gz_bytes) / 1024, 1)
        LOGGER.info(f"[BACKUP] Đã tạo bản sao lưu '{filename}' ({file_size_kb} KB)")

        return JSONResponse(content={
            "status": "success",
            "message": f"Đã tạo bản sao lưu '{filename}' thành công!",
            "filename": filename,
            "size_kb": file_size_kb,
            "stats": backup_data["stats"],
            "created_at": backup_data["created_at"]
        })
    except Exception as e:
        LOGGER.error(f"[BACKUP CREATE] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/music/backup/snapshots")
async def list_backup_snapshots(_: bool = Depends(require_auth)):
    """Lấy danh sách các bản sao lưu đang có trên máy chủ"""
    try:
        snapshots = []
        if os.path.exists(BACKUP_DIR):
            for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
                if fname.endswith(".json") or fname.endswith(".json.gz"):
                    fpath = os.path.join(BACKUP_DIR, fname)
                    stat = os.stat(fpath)
                    from datetime import datetime
                    created_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    snapshots.append({
                        "filename": fname,
                        "size_kb": round(stat.st_size / 1024, 1),
                        "created_at": created_str,
                        "timestamp": stat.st_mtime
                    })
        return JSONResponse(content={"status": "success", "count": len(snapshots), "snapshots": snapshots})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/music/backup/snapshots/{filename}")
async def download_specific_snapshot(filename: str, _: bool = Depends(require_auth)):
    """Tải về một bản snapshot cụ thể từ máy chủ"""
    safe_name = os.path.basename(filename)
    fpath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Không tìm thấy file sao lưu")

    media_type = "application/gzip" if safe_name.endswith(".gz") else "application/json"
    return FileResponse(
        path=fpath,
        media_type=media_type,
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'}
    )


@router.post("/api/music/backup/restore-snapshot")
async def restore_from_snapshot(payload: dict, _: bool = Depends(require_auth)):
    """Khôi phục toàn bộ dữ liệu từ một bản snapshot trên máy chủ"""
    filename = payload.get("filename", "").strip()
    if not filename:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu tên file snapshot"})

    safe_name = os.path.basename(filename)
    fpath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(fpath):
        return JSONResponse(status_code=404, content={"status": "error", "message": f"Không tìm thấy file '{safe_name}'"})

    try:
        with open(fpath, "rb") as f:
            raw_content = f.read()

        if len(raw_content) >= 2 and raw_content[:2] == b'\x1f\x8b':
            raw_content = gzip.decompress(raw_content)
        elif len(raw_content) >= 4 and raw_content[:4] == b'PK\x03\x04':
            import zipfile, io
            with zipfile.ZipFile(io.BytesIO(raw_content)) as z:
                json_names = [n for n in z.namelist() if n.endswith('.json') and not n.startswith('__MACOSX')]
                target_name = json_names[0] if json_names else z.namelist()[0]
                raw_content = z.read(target_name)

        backup_data = json.loads(raw_content.decode("utf-8-sig"))
        restored = await _perform_music_restore(backup_data)

        # Xây dựng thông báo kết quả chi tiết
        parts = []
        if "albums" in restored:
            parts.append(f"{restored['albums']} album ({restored.get('tracks', 0)} bài)")
        if "channels" in restored:
            parts.append(f"{restored['channels']} kênh")
        if "playlists" in restored:
            parts.append(f"{restored['playlists']} playlist")
        if "artists" in restored:
            parts.append(f"{restored['artists']} ca sĩ")
        detail_msg = f" ({', '.join(parts)})" if parts else ""

        return JSONResponse(content={
            "status": "success",
            "message": f"Khôi phục từ bản sao lưu '{safe_name}' thành công!{detail_msg}",
            "restored": restored
        })
    except Exception as e:
        LOGGER.error(f"[RESTORE SNAPSHOT] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi khôi phục: {e}"})


@router.post("/api/music/backup/restore-upload")
async def restore_from_upload(file: UploadFile = File(...), _: bool = Depends(require_auth)):
    """Khôi phục dữ liệu từ file sao lưu người dùng tải lên từ máy tính (.json, .json.gz hoặc .zip)"""
    try:
        content = await file.read()
        if not content:
            return JSONResponse(status_code=400, content={"status": "error", "message": "File tải lên bị rỗng (0 bytes)."})

        # Giải nén Gzip nếu header là \x1f\x8b
        if len(content) >= 2 and content[:2] == b'\x1f\x8b':
            try:
                content = gzip.decompress(content)
            except Exception as gz_err:
                LOGGER.warning(f"[RESTORE UPLOAD] Gzip decompress failed: {gz_err}")
        # Giải nén ZIP nếu header là PK\x03\x04
        elif len(content) >= 4 and content[:4] == b'PK\x03\x04':
            import zipfile, io
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    json_names = [n for n in z.namelist() if n.endswith('.json') and not n.startswith('__MACOSX')]
                    target_name = json_names[0] if json_names else z.namelist()[0]
                    content = z.read(target_name)
            except Exception as zip_err:
                LOGGER.warning(f"[RESTORE UPLOAD] ZIP extract failed: {zip_err}")

        try:
            backup_data = json.loads(content.decode("utf-8-sig"))
        except Exception as json_err:
            return JSONResponse(status_code=400, content={"status": "error", "message": f"Không thể đọc nội dung file JSON: {json_err}"})

        restored = await _perform_music_restore(backup_data)

        # Lưu lại 1 bản sao trên máy chủ luôn để làm snapshot an toàn
        try:
            from datetime import datetime
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            save_name = f"uploaded_{ts_str}.json.gz"
            gz_bytes = gzip.compress(content, compresslevel=6)
            with open(os.path.join(BACKUP_DIR, save_name), "wb") as f:
                f.write(gz_bytes)
        except Exception:
            pass

        # Xây dựng thông báo kết quả chi tiết
        parts = []
        if "albums" in restored:
            parts.append(f"{restored['albums']} album ({restored.get('tracks', 0)} bài)")
        if "channels" in restored:
            parts.append(f"{restored['channels']} kênh")
        if "playlists" in restored:
            parts.append(f"{restored['playlists']} playlist")
        if "artists" in restored:
            parts.append(f"{restored['artists']} ca sĩ")
        detail_msg = f" ({', '.join(parts)})" if parts else ""

        return JSONResponse(content={
            "status": "success",
            "message": f"Đã khôi phục thành công từ '{file.filename}'!{detail_msg}",
            "restored": restored
        })
    except Exception as e:
        LOGGER.error(f"[RESTORE UPLOAD] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi đọc file sao lưu: {e}"})


@router.delete("/api/music/backup/snapshots/{filename}")
async def delete_backup_snapshot(filename: str, _: bool = Depends(require_auth)):
    """Xóa một bản sao lưu trên máy chủ"""
    safe_name = os.path.basename(filename)
    fpath = os.path.join(BACKUP_DIR, safe_name)
    if not os.path.exists(fpath):
        return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy file"})

    try:
        os.remove(fpath)
        return JSONResponse(content={"status": "success", "message": f"Đã xóa bản sao lưu '{safe_name}'"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

