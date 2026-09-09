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


def _safe_int(value: Any) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _format_sample_rate(sample_rate_hz: int) -> str:
    if sample_rate_hz <= 0:
        return ""
    khz = sample_rate_hz / 1000.0
    if khz.is_integer():
        return f"{int(khz)} kHz"
    return f"{khz:g} kHz"


def _codec_display_name(codec_name: str, fallback_ext: str = "") -> str:
    codec = (codec_name or "").strip().lower()
    aliases = {
        "flac": "FLAC",
        "mp3": "MP3",
        "aac": "AAC",
        "alac": "ALAC",
        "opus": "OPUS",
        "vorbis": "OGG",
        "ape": "APE",
        "wavpack": "WV",
    }
    if codec in aliases:
        return aliases[codec]
    if codec.startswith("pcm_"):
        return "WAV" if fallback_ext in ("WAV", "WAVE") else "PCM"
    if codec.startswith("dsd_"):
        return "DSD"
    if codec:
        return codec.upper()
    return fallback_ext or "AUDIO"


def probe_audio_metadata(file_path: str) -> dict:
    """Read authoritative audio properties from a local file with ffprobe."""
    if not file_path or not os.path.isfile(file_path):
        return {}

    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        for candidate in ("/usr/bin/ffprobe", "/usr/local/bin/ffprobe", "/bin/ffprobe"):
            if os.path.isfile(candidate):
                ffprobe_bin = candidate
                break

    if not ffprobe_bin:
        return {}

    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,bits_per_raw_sample,bits_per_sample,bit_rate,channels,channel_layout,duration:format=duration,bit_rate",
        "-of", "json",
        file_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=8,
            check=False,
        )
        if result.returncode != 0 or not result.stdout:
            LOGGER.debug("[AUDIO PROBE] ffprobe failed for %s: %s", file_path, result.stderr.strip())
            return {}

        payload = json.loads(result.stdout)
        streams = payload.get("streams") or []
        stream = streams[0] if streams else {}
        fmt = payload.get("format") or {}

        stream_bitrate = _safe_int(stream.get("bit_rate"))
        format_bitrate = _safe_int(fmt.get("bit_rate"))
        stream_duration = _safe_float(stream.get("duration"))
        format_duration = _safe_float(fmt.get("duration"))

        return {
            "codec_name": str(stream.get("codec_name") or "").strip().lower(),
            "sample_rate": _safe_int(stream.get("sample_rate")),
            "bits_per_raw_sample": _safe_int(stream.get("bits_per_raw_sample")),
            "bits_per_sample": _safe_int(stream.get("bits_per_sample")),
            "bit_rate": stream_bitrate or format_bitrate,
            "channels": _safe_int(stream.get("channels")),
            "channel_layout": str(stream.get("channel_layout") or "").strip(),
            "duration": stream_duration or format_duration,
        }
    except Exception as exc:
        LOGGER.debug("[AUDIO PROBE] ffprobe error on %s: %s", file_path, exc)
        return {}


def detect_audio_quality(
    file_name: str = "",
    mime_type: str = "",
    file_size_bytes: int = 0,
    duration_sec: int = 0,
    caption_text: str = "",
    probe_data: Optional[dict] = None,
) -> tuple[str, str, int]:
    """
    Phân tích chất lượng âm thanh, ưu tiên metadata thực từ ffprobe.

    Khi probe_data có dữ liệu, codec/sample-rate/bit-depth/bitrate được lấy từ
    stream thực. Filename/caption và phép tính file-size/duration chỉ là fallback
    cho các bài Telegram chưa có file local để probe.
    
    Returns:
        (format_string, quality_tier, bitrate_kbps)
        format_string: 'FLAC • 24-bit / 96 kHz • 2,834 kbps', 'MP3 • 320 kbps'
        quality_tier: 'hi-res' | 'lossless' | 'hq' | 'standard'
    """
    ext = os.path.splitext(file_name)[1].lower().replace(".", "").upper() if file_name else ""
    if not ext:
        ext = mime_type.split("/")[-1].upper() if "/" in mime_type else "AUDIO"
    if ext == "MPEG":
        ext = "MP3"

    probe = probe_data if isinstance(probe_data, dict) else {}
    probe_codec = str(probe.get("codec_name") or "").strip().lower()
    probe_sample_rate = _safe_int(probe.get("sample_rate"))
    probe_bit_depth = _safe_int(probe.get("bits_per_raw_sample")) or _safe_int(probe.get("bits_per_sample"))
    probe_bitrate = _safe_int(probe.get("bit_rate"))
    probe_duration = _safe_float(probe.get("duration"))

    if probe_codec or probe_sample_rate or probe_bit_depth or probe_bitrate:
        codec_label = _codec_display_name(probe_codec, ext)
        bitrate_kbps = int(round(probe_bitrate / 1000)) if probe_bitrate > 0 else 0

        # Some containers/codecs do not expose stream bit_rate. In that case use
        # the measured file-size/duration ratio, but never infer bit depth from it.
        measured_duration = probe_duration or float(duration_sec or 0)
        if bitrate_kbps <= 0 and measured_duration > 0 and file_size_bytes > 0:
            bitrate_kbps = int(round((file_size_bytes * 8) / (measured_duration * 1000)))

        sample_rate_text = _format_sample_rate(probe_sample_rate)
        detail_parts = []
        if probe_bit_depth > 0 and sample_rate_text:
            detail_parts.append(f"{probe_bit_depth}-bit / {sample_rate_text}")
        elif probe_bit_depth > 0:
            detail_parts.append(f"{probe_bit_depth}-bit")
        elif sample_rate_text:
            detail_parts.append(sample_rate_text)
        if bitrate_kbps > 0:
            detail_parts.append(f"{bitrate_kbps:,} kbps")

        format_string = codec_label
        if detail_parts:
            format_string += " • " + " • ".join(detail_parts)

        is_dsd = probe_codec.startswith("dsd_") or codec_label == "DSD"
        is_lossless = is_dsd or probe_codec in {"flac", "alac", "ape", "wavpack"} or probe_codec.startswith("pcm_")
        if is_dsd:
            tier = "hi-res"
        elif is_lossless:
            tier = "hi-res" if (probe_bit_depth >= 24 or probe_sample_rate >= 48000) else "lossless"
        elif probe_codec in {"mp3", "aac"}:
            tier = "hq" if bitrate_kbps >= 256 else "standard"
        elif probe_codec in {"opus", "vorbis"}:
            tier = "hq" if bitrate_kbps >= 160 else "standard"
        else:
            tier = "hq" if bitrate_kbps >= 256 else "standard"

        return (format_string, tier, bitrate_kbps)

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
            br_str = f" • ~{bitrate_kbps:,} kbps" if bitrate_kbps else ""
            return (f"{ext} • {bit_depth}-bit / {sample_rate.replace('kHz', ' kHz')}{br_str}", tier, bitrate_kbps)
        elif bit_depth in [24, 32]:
            sr_str = f" / {sample_rate.replace('kHz', ' kHz')}" if sample_rate else ""
            br_str = f" • ~{bitrate_kbps:,} kbps" if bitrate_kbps else ""
            return (f"{ext} • {bit_depth}-bit{sr_str}{br_str}", "hi-res", bitrate_kbps)
        elif sample_rate in ["88.2kHz", "96kHz", "176.4kHz", "192kHz"]:
            br_str = f" • ~{bitrate_kbps:,} kbps" if bitrate_kbps else ""
            return (f"{ext} • {sample_rate.replace('kHz', ' kHz')}{br_str}", "hi-res", bitrate_kbps)

        # Container is lossless, but file size alone does not prove bit depth or sample rate.
        br_str = f" • ~{bitrate_kbps:,} kbps" if bitrate_kbps > 0 else ""
        return (f"{ext} Lossless{br_str}", "lossless", bitrate_kbps)

    # 3. MP3
    if ext == "MP3":
        effective_br = explicit_br or bitrate_kbps
        if effective_br <= 0:
            return ("MP3", "standard", 0)
        tier = "hq" if effective_br >= 256 else "standard"
        prefix = "" if explicit_br else "~"
        return (f"MP3 • {prefix}{effective_br:,} kbps", tier, effective_br)

    # 4. AAC / M4A
    if ext in ["AAC", "M4A"]:
        if "alac" in combined or "lossless" in combined or bitrate_kbps >= 650:
            return (f"ALAC Lossless • ~{bitrate_kbps:,} kbps" if bitrate_kbps else "Apple Lossless (ALAC)", "lossless", bitrate_kbps)
        effective_br = explicit_br or bitrate_kbps
        if effective_br <= 0:
            return ("AAC", "standard", 0)
        tier = "hq" if effective_br >= 256 else "standard"
        prefix = "" if explicit_br else "~"
        return (f"AAC • {prefix}{effective_br:,} kbps", tier, effective_br)

    # 5. OGG / OPUS
    if ext in ["OGG", "OPUS"]:
        br_str = f" • {bitrate_kbps} kbps" if bitrate_kbps > 0 else ""
        tier = "hq" if bitrate_kbps >= 160 else "standard"
        return (f"{ext}{br_str}", tier, bitrate_kbps)

    # 6. Unknown codecs: bitrate alone cannot prove lossless/Hi-Res quality.
    br_str = f" • ~{bitrate_kbps:,} kbps" if bitrate_kbps > 0 else ""
    return (f"{ext}{br_str}", "standard", bitrate_kbps)


def detect_audio_quality_from_track_info(track: dict) -> tuple[str, str, int]:
    name = track.get("name") or track.get("title") or track.get("file_name") or ""
    size_bytes = track.get("size_bytes") or _parse_size_str(track.get("size", ""))
    duration_sec = track.get("duration_sec") or _parse_duration_str(track.get("duration", ""))
    return detect_audio_quality(
        file_name=name,
        mime_type="",
        file_size_bytes=size_bytes,
        duration_sec=duration_sec,
        caption_text="",
        probe_data=track.get("audioProbe") if isinstance(track.get("audioProbe"), dict) else None,
    )


def detect_genre_from_track_info(track: dict) -> str:
    """
    Tự động phân loại thể loại âm nhạc đa dạng và chính xác:
    - Bolero / Trữ Tình (🎻)
    - Pop / Ballad (💖)
    - EDM / Remix / Vinahouse (⚡)
    - Rap / Hip-Hop (🎤)
    - R&B / Soul (🎷)
    - Lofi / Chillout (☕)
    - Acoustic / Instrumental (🎸)
    - Rock / Metal / Indie (🤘)
    - Jazz / Blues (🎺)
    - Nhạc Phim / Anime / OST (🎬)
    - Cổ Điển / Classical (🎼)
    - Nhạc Đỏ / Cách Mạng (⭐)
    - Country / Nhạc Đồng Quê (🌾)
    - Latin / Reggae (🌴)
    - Thiếu Nhi / Kids (🎈)
    - Podcast / Sách Nói (🎙️)
    """
    raw_genre = str(track.get("genre") or "").strip().lower()
    name = str(track.get("name") or track.get("title") or track.get("file_name") or "").lower()
    artist = str(track.get("artist") or "").lower()
    album = str(track.get("album") or "").lower()
    caption = str(track.get("caption") or "").lower()
    combined = f"{raw_genre} {name} {artist} {album} {caption}"

    # 1. Nhạc Thiếu Nhi / Kids
    if any(k in combined for k in ["thiếu nhi", "thieu nhi", "trẻ em", "mầm non", "nursery", "kids", "baby", "chú ếch con", "chị ong nâu"]):
        return "Thiếu Nhi / Kids"

    # 2. Podcast / Audio Book / Sách Nói
    if any(k in combined for k in ["podcast", "audiobook", "sách nói", "sach noi", "truyện audio", "đọc truyện", "talkshow", "radio", "tâm sự"]):
        return "Podcast / Sách Nói"

    # 3. Bolero / Trữ Tình / Dân Ca
    if any(k in combined for k in ["bolero", "trữ tình", "tru tinh", "nhạc vàng", "nhac vang", "sến", "tân cổ", "vọng cổ", "quê hương", "dân ca", "dan ca", "tiền chiến", "cải lương"]):
        return "Bolero / Trữ Tình"

    # 4. Nhạc Đỏ / Cách Mạng / Tiền Tuyến
    if any(k in combined for k in ["nhạc đỏ", "nhac do", "cách mạng", "cach mang", "tiền tuyến", "quân đội", "hành khúc", "đoàn quân", "bác hồ", "bộ đội"]):
        return "Nhạc Đỏ / Cách Mạng"

    # 5. EDM / Remix / Vinahouse / Dance
    if any(k in combined for k in ["vinahouse", "nonstop", "remix", "edm", "dance", "club mix", "dj ", "dj-", "house", "techno", "trance", "electro", "dubstep", "dnb", "drum and bass", "basshouse", "hardstyle", "gym", "workout", "bounce", "psytrance"]):
        return "EDM / Remix"

    # 6. Rap / Hip-Hop / Trap
    if any(k in combined for k in ["rap", "hip hop", "hip-hop", "hiphop", "trap", "drill", "underground", "viet rap", "boombap", "freestyle", "cypher"]):
        return "Rap / Hip-Hop"

    # 7. R&B / Soul / Funk
    if any(k in combined for k in ["r&b", "rnb", "soul", "neo-soul", "funk", "groove", "motown"]):
        return "R&B / Soul"

    # 8. Lofi / Chillout / Ambient
    if any(k in combined for k in ["lofi", "lo-fi", "chill", "chillout", "sleep", "study", "ambient", "meditation", "thư giãn", "thu gian", "rain sound"]):
        return "Lofi / Chill"

    # 9. Acoustic / Instrumental / Không Lời
    if any(k in combined for k in ["acoustic", "guitar", "piano", "không lời", "khong loi", "instrumental", "fingerstyle", "violin", "cello", "saxophone", "hòa tấu", "hoa tau", "độc tấu", "doc tau"]):
        return "Acoustic / Instrumental"

    # 10. Nhạc Phim / Anime / OST / Soundtrack
    if any(k in combined for k in ["soundtrack", " ost", "ost ", "score", "anime", "cinematic", "nhạc phim", "nhac phim", "film score", "bgm", "theme song", "original soundtrack"]):
        return "Nhạc Phim / OST"

    # 11. Cổ Điển / Classical
    if any(k in combined for k in ["classical", "cổ điển", "co dien", "symphony", "concerto", "sonata", "orchestra", "giao hưởng", "giao huong", "mozart", "beethoven", "chopin", "bach", "vivaldi", "tchaikovsky"]):
        return "Cổ Điển / Classical"

    # 12. Rock / Metal / Indie
    if any(k in combined for k in ["rock", "metal", "hard rock", "punk", "alternative", "grunge", "heavy metal", "indie rock", "indie pop", "indie"]):
        return "Rock / Indie"

    # 13. Jazz / Blues
    if any(k in combined for k in ["jazz", "blues", "smooth jazz", "bossa nova", "swing", "bebop", "fusion"]):
        return "Jazz / Blues"

    # 14. Country / Nhạc Đồng Quê
    if any(k in combined for k in ["country", "folk", "bluegrass", "americana", "đồng quê", "dong que"]):
        return "Country / Folk"

    # 15. Latin / Reggae
    if any(k in combined for k in ["latin", "reggaeton", "salsa", "bachata", "reggae", "dancehall", "flamenco", "tango", "cumbia"]):
        return "Latin / Reggae"

    # 16. Pop / Ballad / Nhạc Trẻ
    if any(k in combined for k in ["pop", "ballad", "nhạc trẻ", "nhac tre", "synth-pop", "dance-pop", "k-pop", "kpop", "v-pop", "vpop", "c-pop", "cpop", "j-pop", "jpop"]):
        return "Pop / Ballad"

    return "Khác"


def detect_country_from_track_info(track: dict) -> str:
    """
    Tự động nhận diện Quốc gia / Khu vực của bài hát:
    - Việt Nam (🇻🇳)
    - Âu Mỹ (US-UK) (🇺🇸)
    - Hàn Quốc (K-Pop) (🇰🇷)
    - Hoa Ngữ (C-Pop) (🇨🇳)
    - Nhật Bản (J-Pop) (🇯🇵)
    - Quốc Tế / Khác (🌍)
    """
    name = track.get("name") or track.get("title") or track.get("file_name") or ""
    artist = track.get("artist") or ""
    album = track.get("album") or ""
    caption = track.get("caption") or ""
    combined = f"{name} {artist} {album} {caption}".lower()
    raw_combined = f"{name} {artist} {album} {caption}"

    # 1. Nhận diện Tiếng Việt / V-Pop
    vn_regex = re.compile(r'[àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ]')
    if vn_regex.search(raw_combined):
        return "Việt Nam"
    
    vn_keywords = [
        "v-pop", "vpop", "nhạc việt", "nhac viet", "bolero", "trữ tình", "tru tinh", "nhạc vàng", "nhac vang",
        "rap việt", "rap viet", "lời việt", "loi viet", "nhạc trẻ", "nhac tre", "sơn tùng", "sontung", "m-tp",
        "mtp", "den vau", "đen vâu", "b ray", "karik", "justatee", "soobin", "hieuthuhai", "mono", "erik",
        "đức phúc", "duc phuc", "mỹ tâm", "my tam", "hồ ngọc hà", "ho ngoc ha", "đan trường", "dan truong",
        "trịnh công sơn", "trinh cong son", "lệ quyên", "le quyen", "quang dũng", "bằng kiều", "như quỳnh",
        "min", "amee", "phương ly", "văn mai hương", "hòa minzy", "hoa minzy", "trung quân", "thùy chi",
        "phan mạnh quỳnh", "jack 97", "j97", "chilles", "chillies", "ngọt", "vũ.", "hoàng dũng"
    ]
    if any(k in combined for k in vn_keywords):
        return "Việt Nam"

    # 2. Nhận diện Hàn Quốc / K-Pop (Hangul & K-Pop artists)
    korean_regex = re.compile(r'[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]')
    if korean_regex.search(raw_combined):
        return "Hàn Quốc"

    kr_keywords = [
        "k-pop", "kpop", "korean", "hangul", "ost hàn", "kdrama", "bts", "blackpink", "iu", "exo", "twice",
        "newjeans", "stray kids", "bigbang", "snsd", "girls' generation", "red velvet", "seventeen", "ive",
        "aespa", "taeyeon", "psy", "g-dragon", "nct", "enhypen", "tomorrow x together", "txt", "itzy",
        "lesserafim", "le sserafim", "shinee", "super junior", "monsta x", "mamamoo", "ateez", "got7",
        "gfriend", "stayc", "treasure", "nmixx", "day6", "akmu", "bol4", "baekhyun", "jungkook", "jimin",
        "v (bts)", "rose", "jennie", "lisa", "jisoo", "chungha", "sunmi", "hyuna", "heize",
        "davichi", "paul kim", "zico", "crush", "dean"
    ]
    if any(k in combined for k in kr_keywords):
        return "Hàn Quốc"

    # 3. Nhận diện Nhật Bản / J-Pop (Hiragana, Katakana & J-Pop artists)
    jp_regex = re.compile(r'[\u3040-\u309f\u30a0-\u30ff]')
    if jp_regex.search(raw_combined):
        return "Nhật Bản"

    jp_keywords = [
        "j-pop", "jpop", "anime", "japanese", "utada hikaru", "yoasobi", "kenshi yonezu", "lisa (jp)",
        "aimer", "radwimps", "one ok rock", "official hige dandism", "x japan", "milet", "ayumi hamasaki",
        "namie amuro", "kana nishino", "king gnu", "ado", "eve", "vocaloid", "hatsune miku", "flow",
        "asian kung-fu generation", "spyair", "babymetal", "garnidelia", "sawano hiroyuki", "joe hisaishi"
    ]
    if any(k in combined for k in jp_keywords):
        return "Nhật Bản"

    # 4. Nhận diện Hoa Ngữ / C-Pop (Hanzi & Chinese artists)
    cn_regex = re.compile(r'[\u4e00-\u9fff]')
    if cn_regex.search(raw_combined):
        return "Hoa Ngữ"

    cn_keywords = [
        "c-pop", "cpop", "mandopop", "cantopop", "nhạc hoa", "nhac hoa", "nhạc trung", "nhac trung",
        "lời hoa", "jay chou", "châu kiệt luân", "vương phi", "faye wong", "lâm tuấn kiệt", "jj lin",
        "đặng tử kỳ", "g.e.m", "g.e.m.", "lý vinh hạo", "tiêu chiến", "vương nhất bác", "tiêu kính đằng",
        "trương học hữu", "lưu đức hoa", "quách phú thành", "lê minh", "trần dịch tấn", "eason chan",
        "châu thâm", "zhou shen", "phượng hoàng truyền kỳ", "uông tô lang", "uông phong", "hoa thần vũ"
    ]
    if any(k in combined for k in cn_keywords):
        return "Hoa Ngữ"

    # 5. Nhận diện Âu Mỹ (US-UK)
    usuk_keywords = [
        "us-uk", "usuk", "taylor swift", "shania twain", "daft punk", "the weeknd", "bruno mars", "adele",
        "ed sheeran", "ariana grande", "justin bieber", "drake", "eminem", "coldplay", "maroon 5",
        "billie eilish", "dua lipa", "beyonce", "michael jackson", "queen", "beatles", "the beatles",
        "post malone", "lady gaga", "rihanna", "katy perry", "shawn mendes", "charlie puth", "selena gomez",
        "camila cabello", "imagine dragons", "linkin park", "avicii", "alan walker", "marshmello",
        "chainsmokers", "david guetta", "calvin harris", "sia", "sam smith", "harry styles", "one direction",
        "avril lavigne", "britney spears", "celine dion", "whitney houston", "mariah carey", "madonna",
        "elton john", "bon jovi", "guns n' roses", "ac/dc", "metallica", "nirvana", "green day",
        "twenty one pilots", "republic records", "columbia records", "mercury records", "interscope"
    ]
    if any(k in combined for k in usuk_keywords):
        return "Âu Mỹ"

    # 6. Fallback Quốc Tế / Khác
    return "Âu Mỹ" if any(k in combined for k in ["flac", "edition", "version", "feat", "ft.", "deluxe", "remaster"]) else "Quốc Tế"


def detect_year_from_track_info(track: dict) -> str:
    """
    Tự động nhận diện năm phát hành từ thông tin bài hát / tên file / caption.
    """
    y = track.get("year")
    if y:
        y_str = str(y).strip()
        m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', y_str)
        if m:
            return m.group(1)

    name = track.get("name") or track.get("title") or track.get("file_name") or ""
    album = track.get("album") or ""
    caption = track.get("caption") or ""
    combined = f"{name} {album} {caption}"

    # Search for (2021) or [2021] or 2021 in text
    m = re.search(r'[\(\[\s\-_](19\d{2}|20[0-2]\d)[\)\]\s\-_]', combined)
    if m:
        return m.group(1)

    m = re.search(r'\b(19\d{2}|20[0-2]\d)\b', combined)
    if m:
        return m.group(1)

    return "2024"


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
    tier = str(track.get("qualityTier", "standard") or "standard").lower()
    
    # Parse bitrate an toàn từ int hoặc str (ví dụ "320 kbps", "Lossless", 320)
    raw_br = track.get("bitrate", 0)
    bitrate = 0
    if isinstance(raw_br, (int, float)):
        bitrate = int(raw_br)
    elif isinstance(raw_br, str):
        digits = re.findall(r'\d+', raw_br)
        if digits:
            bitrate = int(digits[0])
        elif "hi-res" in raw_br.lower() or "dsd" in raw_br.lower():
            bitrate = 2000
        elif "lossless" in raw_br.lower() or "flac" in raw_br.lower():
            bitrate = 1000

    # Parse size an toàn từ int hoặc str
    raw_size = track.get("size_bytes", 0)
    size = 0
    if isinstance(raw_size, (int, float)) and raw_size > 0:
        size = int(raw_size)
    else:
        size = _parse_size_str(str(track.get("size", "")))

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


