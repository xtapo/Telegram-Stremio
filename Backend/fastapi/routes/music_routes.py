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

from Backend import db
from pyrogram.errors import FloodWait
from Backend.helper.custom_dl import ByteStreamer
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, Userbot, USERBOT_CLIENT_INDEX, multi_clients, work_loads, client_dc_map, client_failures
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


def _parse_size_str(s: str) -> int:
    if not s:
        return 0
    s = s.strip().upper()
    try:
        parts = s.split()
        if len(parts) >= 2:
            val = float(parts[0])
            unit = parts[1]
            if "GB" in unit: return int(val * 1024 * 1024 * 1024)
            if "MB" in unit: return int(val * 1024 * 1024)
            if "KB" in unit: return int(val * 1024)
            if "B" in unit: return int(val)
    except Exception:
        pass
    return 0


def _parse_duration_str(s: str) -> int:
    if not s or s == "--:--":
        return 0
    try:
        parts = list(map(int, s.strip().split(":")))
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass
    return 0


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def detect_audio_quality(
    file_name: str = "",
    mime_type: str = "",
    file_size_bytes: int = 0,
    duration_sec: int = 0,
    caption_text: str = ""
) -> tuple[str, str, int]:
    """
    Phân tích chính xác chất lượng âm thanh dựa trên:
    - Kích thước file & thời lượng phát (tính Bitrate thực tế kbps)
    - Tên file & Caption (nhận diện tags 24bit, 96kHz, 192kHz, DSD, 320k, MQA,...)
    - Định dạng MIME / Extension (FLAC, WAV, ALAC, DSF, MP3, AAC, OPUS,...)
    
    Returns:
        (format_string, quality_tier, bitrate_kbps)
        format_string: 'FLAC 24-Bit / 96kHz', 'FLAC Lossless 16-Bit', 'MP3 • 320 kbps', 'DSD64 Hi-Res'
        quality_tier: 'hi-res' | 'lossless' | 'hq' | 'standard'
    """
    ext = os.path.splitext(file_name)[1].lower().replace(".", "").upper() if file_name else ""
    if not ext:
        ext = mime_type.split("/")[-1].upper() if "/" in mime_type else "AUDIO"
    if ext == "MPEG":
        ext = "MP3"
    
    bitrate_kbps = 0
    if duration_sec > 0 and file_size_bytes > 0:
        bitrate_kbps = int(round((file_size_bytes * 8) / (duration_sec * 1000)))

    combined = f"{file_name} {caption_text}".lower()

    # Nhận diện Bit Depth (24-bit, 32-bit, 16-bit)
    bit_depth = None
    bd_match = re.search(r'\b(24|32|16)\s*[-_ ]?bit\b|\b(24|32|16)b\b', combined)
    if bd_match:
        m_str = bd_match.group(0)
        if "24" in m_str: bit_depth = 24
        elif "32" in m_str: bit_depth = 32
        elif "16" in m_str: bit_depth = 16

    # Nhận diện Sample Rate (192kHz, 176.4kHz, 96kHz, 88.2kHz, 48kHz, 44.1kHz)
    sample_rate = None
    sr_match = re.search(r'\b(192|176\.4|96|88\.2|48|44\.1)\s*k(?:hz)?\b|\b(192000|96000|88200|48000|44100)\s*hz\b', combined)
    if sr_match:
        raw_sr = sr_match.group(1) or sr_match.group(2) or ""
        if raw_sr in ["192000", "192"]: sample_rate = "192kHz"
        elif raw_sr in ["96000", "96"]: sample_rate = "96kHz"
        elif raw_sr in ["88200", "88.2"]: sample_rate = "88.2kHz"
        elif raw_sr in ["48000", "48"]: sample_rate = "48kHz"
        elif raw_sr in ["44100", "44.1"]: sample_rate = "44.1kHz"
        elif raw_sr in ["176.4"]: sample_rate = "176.4kHz"

    # Nhận diện DSD
    dsd_match = re.search(r'\b(dsd\s*512|dsd\s*256|dsd\s*128|dsd\s*64|dsd)\b', combined)
    
    # Nhận diện Bitrate tag MP3/Lossy
    br_tag_match = re.search(r'\b(320|256|192|128)\s*k(?:bps)?\b', combined)
    explicit_br = int(br_tag_match.group(1)) if br_tag_match else 0

    # 1. DSD / DSF / DFF
    if ext in ["DSF", "DFF"] or dsd_match:
        dsd_tag = dsd_match.group(1).upper().replace(" ", "") if dsd_match else "DSD"
        return (f"{dsd_tag} Hi-Res DSD", "hi-res", bitrate_kbps)

    # 2. FLAC / WAV / ALAC / APE / AIFF (Lossless & Hi-Res)
    if ext in ["FLAC", "WAV", "ALAC", "APE", "AIFF"]:
        if bit_depth and sample_rate:
            is_hires = (bit_depth >= 24) or (sample_rate in ["48kHz", "88.2kHz", "96kHz", "176.4kHz", "192kHz"])
            tier = "hi-res" if is_hires else "lossless"
            label = "Hi-Res" if is_hires else "Lossless"
            return (f"{ext} {label} {bit_depth}-Bit / {sample_rate}", tier, bitrate_kbps)
        elif bit_depth in [24, 32]:
            sr_str = f" / {sample_rate}" if sample_rate else (f" • ~{bitrate_kbps} kbps" if bitrate_kbps else "")
            return (f"{ext} Hi-Res {bit_depth}-Bit{sr_str}", "hi-res", bitrate_kbps)
        elif sample_rate in ["88.2kHz", "96kHz", "176.4kHz", "192kHz"]:
            return (f"{ext} Hi-Res 24-Bit / {sample_rate}", "hi-res", bitrate_kbps)
        
        # Dựa trên Bitrate thực tế tính từ kích thước & thời lượng
        if bitrate_kbps >= 2200:
            return (f"{ext} Hi-Res 24-Bit (~{bitrate_kbps} kbps)", "hi-res", bitrate_kbps)
        elif bitrate_kbps >= 1350:
            return (f"{ext} Hi-Res (~{bitrate_kbps} kbps)", "hi-res", bitrate_kbps)
        elif bitrate_kbps > 0:
            return (f"{ext} Lossless 16-Bit (~{bitrate_kbps} kbps)", "lossless", bitrate_kbps)
        else:
            return (f"{ext} Lossless", "lossless", bitrate_kbps)

    # 3. MP3
    if ext == "MP3":
        effective_br = explicit_br or (bitrate_kbps if bitrate_kbps > 0 else 320)
        tier = "hq" if effective_br >= 256 else "standard"
        return (f"MP3 • {effective_br} kbps", tier, effective_br)

    # 4. AAC / M4A
    if ext in ["AAC", "M4A"]:
        if "alac" in combined or "lossless" in combined or bitrate_kbps >= 650:
            tier = "hi-res" if bitrate_kbps >= 1350 else "lossless"
            label = "Hi-Res" if tier == "hi-res" else "Lossless"
            return (f"ALAC {label} (~{bitrate_kbps} kbps)" if bitrate_kbps else "Apple Lossless (ALAC)", tier, bitrate_kbps)
        effective_br = explicit_br or (bitrate_kbps if bitrate_kbps > 0 else 256)
        tier = "hq" if effective_br >= 256 else "standard"
        return (f"AAC • {effective_br} kbps", tier, effective_br)

    # 5. OGG / OPUS
    if ext in ["OGG", "OPUS"]:
        br_str = f" • {bitrate_kbps} kbps" if bitrate_kbps > 0 else ""
        tier = "hq" if bitrate_kbps >= 160 else "standard"
        return (f"{ext}{br_str}", tier, bitrate_kbps)

    # 6. Fallback
    br_str = f" • {bitrate_kbps} kbps" if bitrate_kbps > 0 else ""
    tier = "hi-res" if bitrate_kbps >= 1350 else ("lossless" if bitrate_kbps >= 600 else "standard")
    return (f"{ext}{br_str}", tier, bitrate_kbps)


def detect_audio_quality_from_track_info(track: dict) -> tuple[str, str, int]:
    name = track.get("name") or track.get("title") or track.get("file_name") or ""
    size_bytes = track.get("size_bytes") or _parse_size_str(track.get("size", ""))
    duration_sec = track.get("duration_sec") or _parse_duration_str(track.get("duration", ""))
    return detect_audio_quality(
        file_name=name,
        mime_type="",
        file_size_bytes=size_bytes,
        duration_sec=duration_sec,
        caption_text=""
    )


def _normalize_str(s: str) -> str:
    if not s:
        return ""
    s = s.lower().strip()
    # Loại bỏ các tag phụ trợ như (Audio), [Official Audio], (Lyric Video), [FLAC], [320kbps]
    s = re.sub(r'[\(\[\{].*?(?:audio|video|lyrics?|flac|mp3|320|lossless|hi-res|master|official|feat|ft\.).*?[\)\]\}]', '', s, flags=re.IGNORECASE)
    return re.sub(r'[^a-zA-Z0-9\u00C0-\u1EF9]', '', s)


def _get_quality_score(track: dict) -> int:
    """
    Tính điểm số chất lượng âm thanh:
    Hi-Res (24-bit/DSD) > Lossless (16-bit FLAC/WAV/ALAC) > High Quality MP3 (320k) > Standard MP3 (128k)
    """
    tier = track.get("qualityTier", "standard")
    bitrate = track.get("bitrate", 0) or 0
    size = track.get("size_bytes", 0) or _parse_size_str(track.get("size", ""))
    
    tier_weights = {
        "hi-res": 3_000_000,
        "lossless": 2_000_000,
        "hq": 1_000_000,
        "standard": 0
    }
    base_score = tier_weights.get(tier, 0)
    return base_score + (bitrate * 10) + min(size // 1024, 9999)


def deduplicate_tracks(tracks: list[dict]) -> tuple[list[dict], int]:
    """
    Tự động nhận diện & loại bỏ bài hát trùng lặp:
    1. Lọc trùng cùng Message ID Telegram (chat_id, msg_id).
    2. Lọc trùng cùng Album + Tên bài hát: Giữ lại bản có chất lượng âm thanh cao nhất.
    
    Returns:
        (unique_tracks, removed_count)
    """
    seen_messages = set()
    unique_by_msg = []
    
    # Bước 1: Lọc trùng theo chat_id & msg_id
    for t in tracks:
        key = (int(t.get("chat_id", 0) or t.get("chatId", 0)), int(t.get("msg_id", 0) or t.get("msgId", 0)))
        if key not in seen_messages:
            seen_messages.add(key)
            unique_by_msg.append(t)

    # Bước 2: Lọc trùng bài hát trong cùng Album (cùng Album + Tên bài hát)
    groups: Dict[tuple, list[dict]] = {}
    for t in unique_by_msg:
        norm_album = _normalize_str(t.get("album", ""))
        norm_title = _normalize_str(t.get("title", "") or t.get("name", ""))
        
        # Nếu không có tên bài thì dùng msg_id để tránh gom nhầm
        if not norm_title:
            group_key = ("__msg__", t.get("msg_id") or t.get("msgId"))
        else:
            group_key = (norm_album, norm_title)
            
        groups.setdefault(group_key, []).append(t)

    final_tracks = []
    removed_count = 0

    for group_key, track_list in groups.items():
        if len(track_list) == 1:
            final_tracks.append(track_list[0])
        else:
            # Sắp xếp theo chất lượng giảm dần -> Giữ bản tốt nhất
            track_list.sort(key=_get_quality_score, reverse=True)
            best_track = track_list[0]
            final_tracks.append(best_track)
            
            dropped_formats = [f"{t.get('format', 'Unknown')} ({t.get('size', '')})" for t in track_list[1:]]
            LOGGER.info(
                f"[MUSIC DEDUP] Giữ bản chất lượng cao: '{best_track.get('title') or best_track.get('name')}' [{best_track.get('format')}] - "
                f"Tự động loại bỏ {len(track_list) - 1} bản trùng: {', '.join(dropped_formats)}"
            )
            removed_count += len(track_list) - 1

    return final_tracks, removed_count


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


CHANNELS_FILE = os.path.join(MUSIC_DIR, "music_channels.json")


# ── MongoDB & JSON Dual-Storage Helpers ──────────────────────────────────────
def _load_channels_file() -> list:
    if os.path.exists(CHANNELS_FILE):
        try:
            with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            LOGGER.error(f"[MUSIC] Error reading channels file: {e}")
    return []


def _save_channels_file(channels: list):
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"[MUSIC] Error saving channels file: {e}")


async def _db_load_channels() -> list:
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            cursor = db.dbs["tracking"]["music_channels"].find()
            docs = [d async for d in cursor]
            if docs:
                channels = [{"id": str(d.get("id") or d.get("_id")), "name": d.get("name", ""), "username": d.get("username", "")} for d in docs]
                _save_channels_file(channels)
                return channels
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not read channels from MongoDB: {e}")
    return _load_channels_file()


async def _db_save_channels(channels: list):
    _save_channels_file(channels)
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            coll = db.dbs["tracking"]["music_channels"]
            curr_ids = [str(c.get("id")) for c in channels]
            if curr_ids:
                await coll.delete_many({"_id": {"$nin": curr_ids}})
                for c in channels:
                    ch_id = str(c.get("id"))
                    await coll.update_one(
                        {"_id": ch_id},
                        {"$set": {"_id": ch_id, "id": ch_id, "name": c.get("name", ""), "username": c.get("username", "")}},
                        upsert=True
                    )
            else:
                await coll.delete_many({})
            LOGGER.info(f"[MUSIC DB] Đã đồng bộ {len(channels)} kênh lên MongoDB.")
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not save channels to MongoDB: {e}")


async def _db_load_library() -> list:
    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            doc = await db.dbs["tracking"]["music_library"].find_one({"_id": "telegram_music_library"})
            if doc and "albums" in doc and isinstance(doc["albums"], list) and len(doc["albums"]) > 0:
                try:
                    os.makedirs(MUSIC_DIR, exist_ok=True)
                    with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(doc["albums"], f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return doc["albums"]
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not read library from MongoDB: {e}")

    if os.path.exists(LIBRARY_CACHE_FILE):
        try:
            with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to load library cache file: {e}")
    return []


async def _db_save_library(albums: list):
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"[MUSIC] Failed to write library cache file: {e}")

    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            await db.dbs["tracking"]["music_library"].update_one(
                {"_id": "telegram_music_library"},
                {"$set": {
                    "_id": "telegram_music_library",
                    "albums": albums,
                    "count": sum(len(a.get("tracks", [])) for a in albums),
                    "updated_at": time.time()
                }},
                upsert=True
            )
            LOGGER.info(f"[MUSIC DB] Đã lưu và đồng bộ {len(albums)} albums lên MongoDB.")
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not sync library to MongoDB: {e}")


# ── 2. Lấy danh sách Albums & Tracks từ MongoDB / Telegram Cache ───────────────
@router.get("/api/music/albums")
async def get_music_albums():
    data = await _db_load_library()
    if data:
        try:
            changed = False
            for alb in data:
                tracks = alb.get("tracks", [])
                if tracks:
                    for t in tracks:
                        t["album"] = alb.get("title", "")
                        current_fmt = t.get("format", "")
                        if not current_fmt or current_fmt in ["FLAC Hi-Res", "MP3 Master", "Hi-Res", "AUDIO Hi-Res", "AUDIO Master"]:
                            fmt, tier, br = detect_audio_quality_from_track_info(t)
                            t["format"] = fmt
                            t["qualityTier"] = tier
                            t["bitrate"] = br
                            changed = True

                    deduped_tracks, removed = deduplicate_tracks(tracks)
                    if removed > 0:
                        for idx, t in enumerate(deduped_tracks, 1):
                            t["id"] = idx
                        alb["tracks"] = deduped_tracks
                        changed = True

                track_formats = [t.get("format", "") for t in alb.get("tracks", [])]
                if track_formats and (not alb.get("format") or alb.get("format") in ["FLAC Hi-Res", "MP3 Master", "Hi-Res"]):
                    hires_fmt = next((f for f in track_formats if "Hi-Res" in f or "24-Bit" in f or "DSD" in f), track_formats[0])
                    alb["format"] = hires_fmt
                    changed = True

            if changed:
                await _db_save_library(data)

            return JSONResponse(content={"status": "success", "source": "database", "albums": data})
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to process library data: {e}")

    return JSONResponse(content={"status": "empty", "source": "none", "albums": []})


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
                saved.append({"id": str(ch), "name": str(ch), "username": ""})
        except Exception:
            pass

    for item in saved:
        ch_id = item.get("id") or item.get("chat_id")
        ch_name = item.get("name") or str(ch_id)
        ch_user = item.get("username") or ""

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
            "username": ch_user
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

    new_ch = {"id": str(resolved_id), "name": ch_name, "username": ch_user}
    saved.append(new_ch)
    await _db_save_channels(saved)
    return {"status": "success", "message": f"Đã thêm kênh '{ch_name}' thành công!", "channel": new_ch}


@router.delete("/api/music/channels/{chat_id}")
async def delete_music_channel(chat_id: str, _: bool = Depends(require_auth)):
    saved = await _db_load_channels()
    new_list = [c for c in saved if str(c.get("id")) != str(chat_id)]
    await _db_save_channels(new_list)
    return {"status": "success", "message": "Đã xóa kênh khỏi danh sách quản lý."}


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
            from Backend.helper.metadata.music_scraper import extract_context_from_text, fetch_music_metadata, clean_audio_filename, parse_artist_and_title

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

                messages_to_process = []

                # ── 1. Quét theo dải ID tin nhắn tùy chỉnh (From -> To) ──
                if from_msg_id > 0:
                    curr_to = to_msg_id
                    if curr_to <= 0 or curr_to < from_msg_id:
                        try:
                            probe = await client.get_messages(resolved_chat_id, list(range(1, 20)))
                            v_ids = [m.id for m in probe if m]
                            curr_to = max(v_ids) if v_ids else from_msg_id + 500
                        except Exception:
                            curr_to = from_msg_id + 500

                    scan_range = list(range(from_msg_id, curr_to + 1))
                    self._log(f"Quét dải ID tin nhắn #{from_msg_id} -> #{curr_to} (Tổng {len(scan_range)} tin nhắn)...")
                    for i in range(0, len(scan_range), 50):
                        if self._cancel_requested:
                            break
                        sub_ids = scan_range[i:i+50]
                        try:
                            b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                            for m in b_msgs:
                                if m:
                                    messages_to_process.append(m)
                        except FloodWait as fw:
                            self._log(f"FloodWait {fw.value}s trong batch — đang tự động chờ...")
                            await asyncio.sleep(fw.value + 1)
                            b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                            for m in b_msgs:
                                if m:
                                    messages_to_process.append(m)
                        except Exception as e:
                            self._log(f"Lỗi lấy cụm tin nhắn {sub_ids[0]}-{sub_ids[-1]}: {e}")
                        await asyncio.sleep(0.04)

                # ── 2. Quét Toàn Bộ Lịch Sử Kênh (limit == 0) ──
                elif limit == 0:
                    self._log("Chế độ quét toàn bộ lịch sử kênh...")
                    try:
                        async for msg in client.get_chat_history(resolved_chat_id):
                            if self._cancel_requested:
                                break
                            if msg:
                                messages_to_process.append(msg)
                    except FloodWait as fw:
                        self._log(f"FloodWait {fw.value}s — đang tự động chờ...")
                        await asyncio.sleep(fw.value + 1)
                        try:
                            async for msg in client.get_chat_history(resolved_chat_id):
                                if self._cancel_requested:
                                    break
                                if msg:
                                    messages_to_process.append(msg)
                        except Exception as e:
                            self._log(f"Thử lại get_chat_history thất bại: {e}")
                    except Exception as hist_err:
                        self._log(f"get_chat_history ({hist_err}), fallback dò batch toàn bộ...")
                        try:
                            probe = await client.get_messages(resolved_chat_id, list(range(1, 20)))
                            v_ids = [m.id for m in probe if m]
                            max_id = max(v_ids) if v_ids else 1000
                            scan_range = list(range(1, max_id + 1))
                            for i in range(0, len(scan_range), 50):
                                if self._cancel_requested:
                                    break
                                sub_ids = scan_range[i:i+50]
                                try:
                                    b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                                    for m in b_msgs:
                                        if m:
                                            messages_to_process.append(m)
                                except FloodWait as fw:
                                    self._log(f"FloodWait {fw.value}s trong batch — đang chờ...")
                                    await asyncio.sleep(fw.value + 1)
                                    b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                                    for m in b_msgs:
                                        if m:
                                            messages_to_process.append(m)
                                await asyncio.sleep(0.04)
                        except Exception as b_err:
                            self._log(f"Lỗi đọc tin nhắn {chat_title}: {b_err}")
                            continue

                # ── 3. Quét theo số lượng tin nhắn gần nhất (limit > 0) ──
                else:
                    try:
                        async for msg in client.get_chat_history(resolved_chat_id, limit=limit):
                            if self._cancel_requested:
                                break
                            if msg:
                                messages_to_process.append(msg)
                    except FloodWait as fw:
                        self._log(f"Telegram yêu cầu tạm dừng {fw.value}s (FloodWait) — đang tự động chờ...")
                        await asyncio.sleep(fw.value + 1)
                        try:
                            async for msg in client.get_chat_history(resolved_chat_id, limit=limit):
                                if self._cancel_requested:
                                    break
                                if msg:
                                    messages_to_process.append(msg)
                        except Exception as e:
                            self._log(f"Thử lại get_chat_history thất bại: {e}")
                    except Exception as hist_err:
                        self._log(f"get_chat_history failed ({hist_err}), thử dò batch...")
                        try:
                            probe = await client.get_messages(resolved_chat_id, list(range(1, 20)))
                            v_ids = [m.id for m in probe if m]
                            max_id = max(v_ids) if v_ids else 100
                            scan_range = list(range(max(1, max_id - limit), max_id + 1))
                            for i in range(0, len(scan_range), 50):
                                if self._cancel_requested:
                                    break
                                sub_ids = scan_range[i:i+50]
                                try:
                                    b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                                    for m in b_msgs:
                                        if m:
                                            messages_to_process.append(m)
                                except FloodWait as fw:
                                    self._log(f"FloodWait {fw.value}s trong batch — đang chờ...")
                                    await asyncio.sleep(fw.value + 1)
                                    b_msgs = await client.get_messages(resolved_chat_id, sub_ids)
                                    for m in b_msgs:
                                        if m:
                                            messages_to_process.append(m)
                                await asyncio.sleep(0.04)
                        except Exception as b_err:
                            self._log(f"Lỗi đọc tin nhắn {chat_title}: {b_err}")
                            continue

                media_group_context = {}
                nearby_text_context = {}
                for msg in messages_to_process:
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

                for m_idx, msg in enumerate(messages_to_process):
                    if self._cancel_requested:
                        break
                    self._processed_messages += 1
                    try:
                        media = getattr(msg, "audio", None) or getattr(msg, "document", None)
                        if not media:
                            continue
                        f_name = getattr(media, "file_name", "") or ""
                        m_type = getattr(media, "mime_type", "") or ""
                        is_audio = bool(getattr(msg, "audio", None)) or m_type.startswith("audio/") or f_name.lower().endswith(audio_extensions)
                        if not is_audio:
                            continue

                        ctx_artist, ctx_album = "", ""
                        mgid = getattr(msg, "media_group_id", None)
                        if mgid and mgid in media_group_context:
                            ctx_artist, ctx_album, _ = media_group_context[mgid]
                        if not ctx_artist and not ctx_album:
                            for offset in range(-5, 6):
                                chk_i = m_idx + offset
                                if 0 <= chk_i < len(messages_to_process):
                                    chk_m = messages_to_process[chk_i]
                                    if chk_m.id in nearby_text_context:
                                        ctx_artist, ctx_album = nearby_text_context[chk_m.id]
                                        break

                        eff_artist = default_artist or ctx_artist
                        eff_album = default_album or ctx_album
                        caption_text = getattr(msg, "caption", "") or ""
                        raw_title = getattr(msg.audio, "title", None) if getattr(msg, "audio", None) else None
                        raw_artist = getattr(msg.audio, "performer", None) if getattr(msg, "audio", None) else None
                        raw_album = getattr(msg.audio, "album", None) if getattr(msg, "audio", None) else None
                        duration_sec = getattr(msg.audio, "duration", 0) if getattr(msg, "audio", None) else 0
                        file_size_bytes = getattr(media, "file_size", 0) or 0

                        audio_fmt, q_tier, calc_br = detect_audio_quality(
                            file_name=f_name, mime_type=m_type, file_size_bytes=file_size_bytes,
                            duration_sec=duration_sec, caption_text=caption_text
                        )
                        has_cover = bool(getattr(media, "thumbs", None))
                        fallback_cover = f"/api/music/cover/{resolved_chat_id}/{msg.id}" if has_cover else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop"

                        scraped_meta = None
                        if auto_scrape:
                            scraped_meta = await fetch_music_metadata(
                                raw_title=raw_title or "",
                                raw_artist=raw_artist or eff_artist or "",
                                raw_album=raw_album or eff_album or "",
                                file_name=f_name or "",
                                caption=caption_text or "",
                                default_artist=eff_artist or "",
                                default_album=eff_album or ""
                            )

                        if scraped_meta:
                            t_title = scraped_meta.get("title") or raw_title or os.path.splitext(f_name)[0] or f"Track {msg.id}"
                            t_artist = scraped_meta.get("artist") or eff_artist or raw_artist or "Unknown Artist"
                            t_album = scraped_meta.get("album") or eff_album or raw_album or chat_title or "Telegram Music Collection"
                            t_cover = scraped_meta.get("cover_url") or fallback_cover
                            t_year = scraped_meta.get("year", time.strftime("%Y"))
                            t_pub = scraped_meta.get("publisher", f"Telegram: {chat_title}")
                        else:
                            p_art, p_tit, p_alb = parse_artist_and_title(raw_title, raw_artist, raw_album, f_name, caption_text)
                            t_title = p_tit or os.path.splitext(f_name)[0] or f"Track {msg.id}"
                            t_artist = eff_artist or p_art or raw_artist or "Unknown Artist"
                            t_album = eff_album or p_alb or raw_album or chat_title or "Telegram Music Collection"
                            t_cover = fallback_cover
                            t_year = time.strftime("%Y")
                            t_pub = f"Telegram: {chat_title}"

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
                            "file_name": f_name,
                            "cover_url": t_cover,
                            "year": t_year,
                            "publisher": t_pub,
                            "stream_url": f"/api/music/stream/{resolved_chat_id}/{msg.id}"
                        })
                        self._found_tracks_count = len(all_scanned_tracks)
                    except Exception:
                        continue

            if self._cancel_requested:
                self._status = "cancelled"
                self._end_time = time.time()
                return

            self._log(f"Quét hoàn tất! Tìm thấy tổng cộng {len(all_scanned_tracks)} bài hát.")

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
                                "file_name": "",
                                "cover_url": t.get("coverUrl", a.get("coverUrl", "")),
                                "year": a.get("year", "2026"),
                                "publisher": a.get("publisher", ""),
                                "stream_url": t.get("previewUrl", "")
                            })
                except Exception as e:
                    self._log(f"Không thể đọc thư viện cũ: {e}")

            combined_pool = existing_tracks + all_scanned_tracks
            combined_pool, dup_removed = deduplicate_tracks(combined_pool)
            self._duplicates_removed = dup_removed

            # Group into Albums
            albums_dict = {}
            for tr in combined_pool:
                alb_name = tr["album"]
                if alb_name not in albums_dict:
                    color_preset = GLOW_PRESETS[len(albums_dict) % len(GLOW_PRESETS)]
                    albums_dict[alb_name] = {
                        "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', alb_name.lower())[:30]}",
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
                alb_obj = albums_dict[alb_name]
                alb_obj["tracks"].append({
                    "id": len(alb_obj["tracks"]) + 1,
                    "name": tr["title"],
                    "artist": tr["artist"],
                    "duration": tr["duration"],
                    "size": tr["size"],
                    "format": tr["format"],
                    "qualityTier": tr["qualityTier"],
                    "bitrate": tr["bitrate"],
                    "previewUrl": tr["stream_url"],
                    "chatId": tr["chat_id"],
                    "msgId": tr["msg_id"],
                    "coverUrl": tr["cover_url"]
                })

            final_albums = list(albums_dict.values())
            for alb in final_albums:
                alb_tracks = [t for t in combined_pool if t["album"].upper() == alb["title"]]
                total_b = sum(t.get("size_bytes", 0) for t in alb_tracks)
                alb["totalSize"] = _format_size(total_b)
                hires_t = next((t for t in alb_tracks if t.get("qualityTier") == "hi-res"), None)
                if hires_t:
                    alb["format"] = hires_t["format"]
                    alb["qualityTier"] = "hi-res"
                elif alb_tracks:
                    alb["format"] = alb_tracks[0]["format"]
                    alb["qualityTier"] = alb_tracks[0].get("qualityTier", "lossless")
                for t in alb["tracks"]:
                    if "/api/music/cover/" in t.get("coverUrl", ""):
                        alb["coverUrl"] = t["coverUrl"]
                        break

            # Lưu vào MongoDB và file JSON
            await _db_save_library(final_albums)

            self._status = "completed"
            self._end_time = time.time()
            self._log(f"Đã lưu thành công {len(final_albums)} albums ({len(combined_pool)} bài hát) vào thư viện.")
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


# ── Async Music Scanner APIs ──────────────────────────────────────────────────
@router.post("/api/music/scan/start")
async def start_music_scan_api(payload: dict, _: bool = Depends(require_auth)):
    channels = payload.get("channels") or []
    if not channels and payload.get("chat_id"):
        channels = [payload.get("chat_id")]
    if not channels:
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 kênh để quét.")

    raw_limit = int(payload.get("limit", 100))
    limit = 0 if raw_limit == 0 else max(raw_limit, 5)
    from_msg_id = max(0, int(payload.get("from_msg_id", 0) or 0))
    to_msg_id = max(0, int(payload.get("to_msg_id", 0) or 0))
    mode = str(payload.get("mode", "append")).lower()
    auto_scrape = bool(payload.get("auto_scrape", True))
    default_artist = str(payload.get("default_artist", "")).strip()
    default_album = str(payload.get("default_album", "")).strip()

    result = await music_scan_manager.start(
        channels=channels,
        limit=limit,
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


# ── 4. Stream trực tiếp Audio từ Telegram với HTTP Range 206 ──────────────────
@router.get("/api/music/stream/{chat_id}/{msg_id}")
@router.head("/api/music/stream/{chat_id}/{msg_id}")
async def stream_music_track(request: Request, chat_id: int, msg_id: int):
    # Ưu tiên Userbot nếu đang kết nối (để đọc được mọi kênh private/public)
    streamer = None
    client_idx = 0
    tg_client = None

    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
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
        LOGGER.warning(f"[MUSIC STREAM] Client {client_idx} failed to get file properties for {chat_id}/{msg_id}: {e}, thử các client khác...")
        
        # Fallback thử lần lượt các client còn lại
        candidates = []
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

    body_gen = await streamer.prefetch_stream(
        file_id=file_id,
        client_index=client_idx,
        offset=offset,
        first_part_cut=first_part_cut,
        last_part_cut=last_part_cut,
        part_count=part_count,
        chunk_size=chunk_size,
        prefetch=2,
        stream_id=stream_id,
        meta=meta,
        parallelism=1,
        request=request,
        chat_id=chat_id,
        message_id=msg_id,
        extra_clients=[],
    )

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


# ── 5. Lấy Ảnh Cover / Thumbnail từ Telegram Message ──────────────────────────
@router.get("/api/music/cover/{chat_id}/{msg_id}")
async def get_music_cover(chat_id: int, msg_id: int):
    cache_key = f"{chat_id}_{msg_id}"
    now = time.time()
    if cache_key in _cover_cache:
        data, mime, exp = _cover_cache[cache_key]
        if now < exp:
            return PlainResponse(content=data, media_type=mime, headers={"Cache-Control": "public, max-age=86400"})

    clients_to_try = []
    active = _get_active_client()
    if active:
        clients_to_try.append(active)
    if StreamBot and StreamBot not in clients_to_try:
        clients_to_try.append(StreamBot)
    if multi_clients:
        for c in multi_clients.values():
            if c not in clients_to_try:
                clients_to_try.append(c)

    data = None
    for cl in clients_to_try:
        try:
            msg = await cl.get_messages(chat_id, msg_id)
            media = getattr(msg, "audio", None) or getattr(msg, "document", None)
            thumbs = getattr(media, "thumbs", None) if media else None
            if thumbs:
                buf = await cl.download_media(thumbs[-1], in_memory=True)
                if buf and hasattr(buf, "getvalue"):
                    data = buf.getvalue()
                    break
        except Exception:
            continue

    if data:
        _cover_cache[cache_key] = (data, "image/jpeg", now + _COVER_CACHE_TTL)
        return PlainResponse(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})

    _cover_cache[cache_key] = (DEFAULT_COVER_SVG, "image/svg+xml", now + 3600)
    return PlainResponse(content=DEFAULT_COVER_SVG, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=3600"})


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
        await _db_save_library(albums)

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

        await _db_save_library(albums)
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
                    matched_tracks.append(t)

        if new_album and matched_tracks:
            for a in albums:
                a["tracks"] = [t for t in a.get("tracks", [])
                               if (int(t.get("chatId", 0)), int(t.get("msgId", 0))) not in id_set]

            dest_album = next((a for a in albums if a.get("title", "").upper() == new_album.upper()), None)
            if not dest_album:
                color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                dest_album = {
                    "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', new_album.lower())[:30]}",
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
        await _db_save_library(albums)

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



