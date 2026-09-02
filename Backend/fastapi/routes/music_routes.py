import asyncio
import json
import math
import mimetypes
import os
import re
import secrets
import time
import unicodedata
from typing import Dict, List, Optional
from urllib.parse import quote, unquote
import httpx

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
from Backend.fastapi.routes.stream_routes import select_best_client, _get_streamer, parse_range_header, _resolve_filename_mime, _build_stream_headers, get_parallel_prefetch
from Backend.fastapi.security.credentials import get_current_user, require_auth
from Backend.fastapi.routes.template_routes import _base_context, templates

router = APIRouter(tags=["Music Player & Telegram Storage"])

MUSIC_DIR = os.path.abspath("Music")
LIBRARY_CACHE_FILE = os.path.join(MUSIC_DIR, "telegram_library.json")
AUDIO_CACHE_DIR = os.path.join(MUSIC_DIR, "cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
MAX_AUDIO_CACHE_SIZE = 2 * 1024 * 1024 * 1024  # 2 GB cache giới hạn tự dọn dẹp

_cover_cache: Dict[str, tuple] = {}
_COVER_CACHE_TTL = 86400

def _clean_audio_cache():
    try:
        if not os.path.exists(AUDIO_CACHE_DIR):
            return
        files = []
        total_size = 0
        for fname in os.listdir(AUDIO_CACHE_DIR):
            fpath = os.path.join(AUDIO_CACHE_DIR, fname)
            if os.path.isfile(fpath):
                stat = os.stat(fpath)
                files.append((fpath, stat.st_atime, stat.st_size))
                total_size += stat.st_size
        
        if total_size > MAX_AUDIO_CACHE_SIZE:
            files.sort(key=lambda x: x[1])
            target_size = int(MAX_AUDIO_CACHE_SIZE * 0.75)
            for fpath, _, fsize in files:
                if total_size <= target_size:
                    break
                try:
                    os.remove(fpath)
                    total_size -= fsize
                    if fpath.endswith(".dat"):
                        meta_f = fpath[:-4] + ".json"
                        if os.path.exists(meta_f):
                            os.remove(meta_f)
                except Exception:
                    pass
    except Exception as e:
        LOGGER.warning(f"[MUSIC CACHE] Lỗi dọn dẹp audio cache: {e}")

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
    tv_param = request.query_params.get("tv") == "1" or request.query_params.get("mode") == "tv" or request.query_params.get("lite") == "1"
    ua = (request.headers.get("user-agent") or "").lower()
    is_tv_ua = any(k in ua for k in ["androidtv", "smarttv", "bravia", "googletv", "mitv", "aftt", "aftm", "shield", "crkey", "telegrammusictv", "leanback"])

    tv_path = os.path.join(MUSIC_DIR, "tv.html")
    index_path = os.path.join(MUSIC_DIR, "index.html")

    if (tv_param or is_tv_ua) and os.path.exists(tv_path):
        return FileResponse(tv_path)

    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h3>Music Player template not found in /Music/index.html</h3>", status_code=404)


@router.get("/tv", response_class=HTMLResponse)
@router.get("/tv/", response_class=HTMLResponse)
@router.get("/tv.html", response_class=HTMLResponse)
@router.get("/music/tv", response_class=HTMLResponse)
@router.get("/music/tv/", response_class=HTMLResponse)
@router.get("/music/tv.html", response_class=HTMLResponse)
@router.get("/music/lite", response_class=HTMLResponse)
@router.get("/Music/tv", response_class=HTMLResponse)
@router.get("/Music/tv/", response_class=HTMLResponse)
@router.get("/Music/tv.html", response_class=HTMLResponse)
@router.get("/Music/lite", response_class=HTMLResponse)
async def get_music_tv_player():
    tv_path = os.path.join(MUSIC_DIR, "tv.html")
    if os.path.exists(tv_path):
        return FileResponse(tv_path)
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h3>TV Lite template not found</h3>", status_code=404)


@router.get("/music/{filename:path}")
async def get_music_static_file(filename: str):
    """
    Phục vụ trực tiếp CSS, JS, Fonts, Images khi người dùng truy cập /music/style.css, /music/app.js, v.v.
    Bảo đảm 100% không bị lỗi 404 trên Linux / Hugging Face.
    """
    if not filename or filename.strip("/") in ["", "index.html"]:
        return FileResponse(os.path.join(MUSIC_DIR, "index.html"), headers={"Cache-Control": "no-cache, must-revalidate"})

    if filename.strip("/") in ["tv", "tv.html", "lite"]:
        tv_path = os.path.join(MUSIC_DIR, "tv.html")
        if os.path.exists(tv_path):
            return FileResponse(tv_path, headers={"Cache-Control": "no-cache, must-revalidate"})

    clean_name = filename.lstrip("/")
    file_path = os.path.join(MUSIC_DIR, clean_name)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".css", ".js", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"]:
            headers = {"Cache-Control": "public, max-age=604800, stale-while-revalidate=86400"}
        else:
            headers = {"Cache-Control": "public, max-age=3600"}
        return FileResponse(file_path, media_type=mime_type, headers=headers)

    # Fallback to index.html if not a static file
    index_path = os.path.join(MUSIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, headers={"Cache-Control": "no-cache, must-revalidate"})
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
                channels = [
                    {
                        "id": str(d.get("id") or d.get("_id")),
                        "name": d.get("name", ""),
                        "username": d.get("username", ""),
                        "last_scanned_id": int(d.get("last_scanned_id", 0) or 0),
                        "last_scanned_at": str(d.get("last_scanned_at", "") or ""),
                        "total_tracks": int(d.get("total_tracks", 0) or 0),
                    }
                    for d in docs
                ]
                _save_channels_file(channels)
                return channels
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not read channels from MongoDB: {e}")
    raw_list = _load_channels_file()
    for item in raw_list:
        item["last_scanned_id"] = int(item.get("last_scanned_id", 0) or 0)
        item["last_scanned_at"] = str(item.get("last_scanned_at", "") or "")
        item["total_tracks"] = int(item.get("total_tracks", 0) or 0)
    return raw_list


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
                    doc = {
                        "_id": ch_id,
                        "id": ch_id,
                        "name": c.get("name", ""),
                        "username": c.get("username", ""),
                        "last_scanned_id": int(c.get("last_scanned_id", 0) or 0),
                        "last_scanned_at": str(c.get("last_scanned_at", "") or ""),
                        "total_tracks": int(c.get("total_tracks", 0) or 0),
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

async def _db_load_library(force_reload: bool = False) -> list:
    global _IN_MEMORY_LIBRARY_CACHE
    if not force_reload and _IN_MEMORY_LIBRARY_CACHE is not None:
        return _IN_MEMORY_LIBRARY_CACHE

    # Đọc từ file cache cục bộ trước để phản hồi tức thì
    if os.path.exists(LIBRARY_CACHE_FILE):
        try:
            with open(LIBRARY_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    _IN_MEMORY_LIBRARY_CACHE = data
                    return data
        except Exception as e:
            LOGGER.error(f"[MUSIC] Failed to load library cache file: {e}")

    try:
        if db and hasattr(db, "dbs") and "tracking" in db.dbs:
            doc = await asyncio.wait_for(
                db.dbs["tracking"]["music_library"].find_one({"_id": "telegram_music_library"}),
                timeout=5.0
            )
            if doc and "albums" in doc and isinstance(doc["albums"], list) and len(doc["albums"]) > 0:
                _IN_MEMORY_LIBRARY_CACHE = doc["albums"]
                try:
                    os.makedirs(MUSIC_DIR, exist_ok=True)
                    with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(doc["albums"], f, ensure_ascii=False)
                except Exception:
                    pass
                return doc["albums"]
    except asyncio.TimeoutError:
        LOGGER.warning("[MUSIC DB] MongoDB load library query timed out (5s). Using fallback.")
    except Exception as e:
        LOGGER.warning(f"[MUSIC DB] Could not read library from MongoDB: {e}")

    return []


async def _db_save_library(albums: list):
    global _IN_MEMORY_LIBRARY_CACHE
    _IN_MEMORY_LIBRARY_CACHE = albums
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(LIBRARY_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(albums, f, ensure_ascii=False)
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


PLAYLISTS_FILE = os.path.join(MUSIC_DIR, "telegram_playlists.json")

def _load_playlists_file() -> list:
    if os.path.exists(PLAYLISTS_FILE):
        try:
            with open(PLAYLISTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def _save_playlists_file(playlists: list):
    try:
        os.makedirs(MUSIC_DIR, exist_ok=True)
        with open(PLAYLISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(playlists, f, ensure_ascii=False, indent=2)
    except Exception as e:
        LOGGER.error(f"[MUSIC] Failed to save playlists: {e}")


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


@router.get("/api/music/playlist/all.m3u8")
@router.get("/api/music/playlist/all")
async def stream_all_music_m3u8(request: Request):
    """Trả về file playlist .m3u8 toàn bộ kho nhạc thư viện"""
    base_url = _get_request_base_url(request)
    data = await _db_load_library() or []
    all_albums = list(data) if data else DEMO_ALBUMS_FALLBACK

    all_tracks = []
    for alb in all_albums:
        for t in alb.get("tracks", []):
            if not t.get("artist"):
                t["artist"] = alb.get("artist", "")
            all_tracks.append(t)

    m3u8_text = _build_m3u8_content("XTAPO_All_Music_Library", all_tracks, base_url)
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
                    "total_tracks": 0
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
            "total_tracks": total_tracks
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
        "total_tracks": 0
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
                scan_range = list(range(scan_from, scan_to + 1))
                self._target_messages = len(scan_range)
                self._log(f"Quét dải ID tin nhắn #{scan_from} -> #{scan_to} (Tổng {len(scan_range)} tin nhắn)...")

                batch_size = 50
                for i in range(0, len(scan_range), batch_size):
                    if self._cancel_requested:
                        break
                    sub_ids = scan_range[i:i + batch_size]
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
                            is_audio = bool(audio_obj) or m_type.startswith("audio/") or f_name.lower().endswith(audio_extensions)
                            if not is_audio:
                                continue

                            caption_text = getattr(msg, "caption", "") or ""
                            raw_title = getattr(audio_obj, "title", None) if audio_obj else None
                            raw_artist = getattr(audio_obj, "performer", None) if audio_obj else None
                            raw_album = getattr(audio_obj, "album", None) if audio_obj else None
                            duration_sec = getattr(audio_obj, "duration", 0) if audio_obj else 0
                            file_size_bytes = getattr(media, "file_size", 0) or 0

                            if not duration_sec and doc_obj:
                                for attr in getattr(doc_obj, "attributes", []) or []:
                                    if hasattr(attr, "duration") and attr.duration:
                                        duration_sec = int(attr.duration)
                                    if hasattr(attr, "performer") and attr.performer and not raw_artist:
                                        raw_artist = attr.performer
                                    if hasattr(attr, "title") and attr.title and not raw_title:
                                        raw_title = attr.title

                            if not duration_sec and file_size_bytes > 0:
                                est_kbps = 900 if ("flac" in f_name.lower() or "wav" in f_name.lower()) else 320
                                duration_sec = max(45, int(file_size_bytes / (est_kbps * 125)))

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

                            fingerprint_cover = None
                            fingerprint_genre = None
                            if final_artist == "Unknown Artist" or final_title.lower().startswith("track") or final_title.lower().startswith("audio") or "track" in f_name.lower():
                                fg_res = await recognize_audio_from_telegram(client, msg, chat_id=resolved_chat_id, msg_id=msg.id)
                                if fg_res:
                                    final_title = fg_res.get("title") or final_title
                                    final_artist = fg_res.get("artist") or final_artist
                                    final_album = fg_res.get("album") or final_album
                                    fingerprint_cover = fg_res.get("cover_url")
                                    fingerprint_genre = fg_res.get("genre")

                            audio_fmt, q_tier, calc_br = detect_audio_quality(
                                file_name=f_name, mime_type=m_type, file_size_bytes=file_size_bytes,
                                duration_sec=duration_sec, caption_text=caption_text
                            )
                            has_cover = bool(getattr(media, "thumbs", None))
                            fallback_cover = fingerprint_cover or (f"/api/music/cover/{resolved_chat_id}/{msg.id}" if has_cover else "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop")

                            scraped_meta = None
                            if auto_scrape:
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
                                t_title = scraped_meta.get("title") or final_title
                                t_artist = scraped_meta.get("artist") or final_artist
                                t_album = scraped_meta.get("album") or final_album
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
                                t_year = time.strftime("%Y")
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
                                "file_name": f_name,
                                "cover_url": t_cover,
                                "year": t_year,
                                "publisher": t_pub,
                                "genre": t_genre,
                                "country": t_country,
                                "era": t_era,
                                "stream_url": f"/api/music/stream/{resolved_chat_id}/{msg.id}"
                            })
                            self._found_tracks_count = len(all_scanned_tracks)
                        except Exception:
                            continue

                    # Cập nhật số tin nhắn đã quét và checkpoint vào DB
                    self._processed_messages += len(sub_ids)
                    checkpoint_to_save = max(highest_seen_id, sub_ids[-1])
                    ch_tracks_total = len([t for t in all_scanned_tracks if str(t.get("chat_id")) == str(resolved_chat_id)])
                    await _db_update_channel_progress(self._current_channel_id, checkpoint_to_save, total_tracks=ch_tracks_total)
                    await asyncio.sleep(0.02)

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
                                "isShazam": bool(t.get("isShazam", False)),
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
                    "coverUrl": tr["cover_url"],
                    "genre": tr.get("genre") or detect_genre_from_track_info(tr),
                    "country": tr.get("country") or detect_country_from_track_info(tr),
                    "isShazam": bool(tr.get("isShazam", False))
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
                
                # Assign country to album
                alb["country"] = detect_country_from_track_info({"name": alb.get("title", ""), "artist": alb.get("artist", ""), "album": alb.get("title", "")})

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


async def _caching_stream_generator(body_gen, cache_key: str, file_name: str, mime_type: str, total_size: int, start_offset: int):
    rand_suffix = secrets.token_hex(4)
    tmp_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}_{rand_suffix}.tmp")
    dat_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.dat")
    json_path = os.path.join(AUDIO_CACHE_DIR, f"{cache_key}.json")
    
    can_cache = (start_offset == 0)
    tmp_file = None
    bytes_written = 0
    
    if can_cache:
        try:
            tmp_file = open(tmp_path, "wb")
        except Exception:
            tmp_file = None
            can_cache = False

    try:
        async for chunk in body_gen:
            if can_cache and tmp_file:
                try:
                    tmp_file.write(chunk)
                    bytes_written += len(chunk)
                except Exception:
                    can_cache = False
                    if tmp_file:
                        try:
                            tmp_file.close()
                        except Exception:
                            pass
                        tmp_file = None
            yield chunk
            await asyncio.sleep(0)
    finally:
        if tmp_file:
            try:
                tmp_file.close()
            except Exception:
                pass
            if can_cache and bytes_written == total_size:
                try:
                    meta = {
                        "file_name": file_name,
                        "mime_type": mime_type,
                        "file_size": total_size,
                        "cached_at": time.time()
                    }
                    with open(json_path, "w", encoding="utf-8") as jf:
                        json.dump(meta, jf)
                    if os.path.exists(dat_path):
                        try:
                            os.remove(dat_path)
                        except Exception:
                            pass
                    os.replace(tmp_path, dat_path)
                    LOGGER.info(f"[MUSIC CACHE] Đã cache thành công bài hát {cache_key} ({_format_size(total_size)})")
                    asyncio.create_task(asyncio.to_thread(_clean_audio_cache))
                except Exception as e:
                    LOGGER.warning(f"[MUSIC CACHE] Lỗi khi hoàn tất lưu cache: {e}")
            else:
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass


# ── 4. Stream trực tiếp Audio từ Telegram với HTTP Range 206 + Multi-Bot + Local Cache ──────────────────
@router.get("/api/music/stream/{chat_id}/{msg_id}")
@router.head("/api/music/stream/{chat_id}/{msg_id}")
async def stream_music_track(request: Request, chat_id: int, msg_id: int):
    cache_key = f"{abs(chat_id)}_{msg_id}"
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

    # Tính toán số lượng worker song song và prefetch an toàn
    token_count = len(multi_clients) - 1 if multi_clients else 0
    parallelism, prefetch_count = get_parallel_prefetch(token_count)
    parallelism = max(1, parallelism)
    prefetch_count = max(4, prefetch_count)

    extra_clients_for_stream = []
    if parallelism > 1 and len(multi_clients) > 1:
        other_indices = sorted((i for i in multi_clients if i != client_idx), key=lambda i: work_loads.get(i, 0))

        async def _get_extra_file_id(ec_idx: int):
            ec_client = multi_clients[ec_idx]
            ec_streamer = _get_streamer(ec_client, ec_idx)
            try:
                ec_fid = await ec_streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
                return (ec_idx, ec_streamer, ec_fid)
            except Exception as e:
                LOGGER.warning("Extra client %s file_id fetch failed: %s", ec_idx, e)
                return None

        results = await asyncio.gather(*[_get_extra_file_id(i) for i in other_indices[:parallelism - 1]])
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

    # Wrap body_gen với cache writer nếu đang tải từ đầu
    cached_stream = _caching_stream_generator(body_gen, cache_key, file_name, mime_type, file_size, start)
    return StreamingResponse(cached_stream, headers=headers, status_code=status, media_type=mime_type)


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

_COVER_SEMAPHORE = asyncio.Semaphore(10)


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
            if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
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
            return {"ok": False, "message": "Đang có tiến trình nhận diện Shazam đang chạy!"}

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

        self._add_log(f"Bắt đầu nhận diện {self._total} bài hát qua Shazam...", "info")
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
                self._add_log(f"🔍 #{idx}/{self._total} Đang phân tích: {orig_name}...", "info")

                fg_res = await recognize_audio_from_telegram(
                    client=None,
                    message=None,
                    is_manual=True,
                    chat_id=chat_id_int,
                    msg_id=msg_id_int,
                )
                await asyncio.sleep(0.2)

                # Fallback online metadata scraper nếu audio fingerprint không khớp
                if not fg_res and curr_track:
                    raw_name = curr_track.get("name", "")
                    raw_artist = curr_track.get("artist", "")
                    if raw_artist.lower() in ["unknown artist", "unknown", "va", "various artists"]:
                        raw_artist = ""
                    scraped = await fetch_music_metadata(
                        raw_title=raw_name,
                        raw_artist=raw_artist,
                        file_name=raw_name
                    )
                    if scraped and scraped.get("title") and scraped.get("artist"):
                        LOGGER.info(f"[SHAZAM FALLBACK] Nhận diện thành công qua Metadata trực tuyến: {scraped.get('artist')} - {scraped.get('title')}")
                        fg_res = {
                            "title": scraped.get("title"),
                            "artist": scraped.get("artist"),
                            "album": scraped.get("album"),
                            "cover_url": scraped.get("cover_url"),
                            "genre": scraped.get("genre")
                        }

                if fg_res:
                    update_fields = {}
                    if fg_res.get("title"): update_fields["name"] = fg_res["title"]
                    if fg_res.get("artist"): update_fields["artist"] = fg_res["artist"]
                    if fg_res.get("album"): update_fields["album"] = fg_res["album"]
                    if fg_res.get("cover_url"): update_fields["coverUrl"] = fg_res["cover_url"]
                    update_fields["isShazam"] = True

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
                            genre_str = f" [{fg_res.get('genre')}]" if fg_res.get('genre') else ""
                            self._add_log(f"✅ #{idx} {fg_res.get('title')} - {fg_res.get('artist')}{genre_str}", "success")
                else:
                    self._failed_count += 1
                    self._add_log(f"⚠️ #{idx} {orig_name}: Không tìm thấy dấu vân tay khớp", "warn")

                # Lưu trung gian mỗi 5 bài
                if idx % 5 == 0 and self._success_count > 0:
                    try:
                        valid_albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
                        await _db_save_library(valid_albums)
                    except Exception:
                        pass

            # Lưu thư viện cuối cùng
            if self._success_count > 0:
                albums = [a for a in albums if a.get("tracks") and len(a["tracks"]) > 0]
                await _db_save_library(albums)

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

async def _search_artist_online_helper(name: str):
    """
    Tìm kiếm thông tin, ảnh chân dung, ảnh fanart 1080p, banner và tiểu sử (Bio)
    từ Deezer, TheAudioDB, Last.fm và Apple Music
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

    # 2. TheAudioDB (Ảnh chân dung, Fanart nền 1080p, Banner, Logo trong suốt, Tiểu sử)
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
                            "type": "fanart",
                            "source": "TheAudioDB Fanart"
                        })
    except Exception as e:
        LOGGER.warning(f"[ARTIST SEARCH] TheAudioDB error for '{cleaned_name}': {e}")

    # 3. Last.fm (Tiểu sử phong phú + Danh sách Tags Thể Loại)
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

    # 4. Apple Music / iTunes (Tìm thêm thể loại chính thức)
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


@router.get("/api/music/artists")
async def get_all_artists():
    """
    Lấy danh sách tất cả ca sĩ được trích xuất từ thư viện nhạc kèm ảnh và metadata
    """
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

        # 2. Lấy metadata đã cache từ MongoDB collection `music_artists`
        coll = db.dbs["tracking"]["music_artists"]
        cached_cursor = coll.find()
        cached_map = {}
        async for doc in cached_cursor:
            cached_map[doc["_id"]] = doc

        # 3. Tổng hợp kết quả
        artists_list = []
        for name, data in artist_map.items():
            slug = name.lower().strip()
            cached = cached_map.get(slug) or cached_map.get(name)
            
            avatar_url = (cached.get("avatar_url") if cached else "") or data["sample_track_cover"] or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop"
            banner_url = (cached.get("banner_url") if cached else "") or avatar_url
            bio = cached.get("bio", "") if cached else ""
            genres = list(set(list(data["genres"]) + (cached.get("genres", []) if cached else [])))

            artists_list.append({
                "name": name,
                "avatar_url": avatar_url,
                "banner_url": banner_url,
                "bio": bio,
                "genres": genres,
                "fans_count": cached.get("fans_count", 0) if cached else 0,
                "has_custom_avatar": bool(cached and cached.get("avatar_url")),
                "tracks_count": data["tracks_count"],
                "albums_count": len(data["albums"]),
                "albums_list": list(data["albums"])
            })

        artists_list.sort(key=lambda x: x["tracks_count"], reverse=True)
        return JSONResponse(content={"status": "success", "count": len(artists_list), "artists": artists_list})
    except Exception as e:
        LOGGER.error(f"[GET ARTISTS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.get("/api/music/artist/search-online")
async def search_artist_online(name: str = Query(..., min_length=1), _: bool = Depends(require_auth)):
    """
    Tìm kiếm ảnh chân dung và profile ca sĩ từ Deezer / Apple Music
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
    Admin cập nhật thông tin và ảnh đại diện cho ca sĩ
    """
    name = payload.get("name", "").strip()
    avatar_url = payload.get("avatar_url", "").strip()
    banner_url = payload.get("banner_url", "").strip()
    bio = payload.get("bio", "").strip()
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
            "genres": genres if isinstance(genres, list) else [],
            "updated_at": time.time()
        }
        
        await coll.update_one({"_id": slug}, {"$set": update_data}, upsert=True)
        return JSONResponse(content={"status": "success", "message": f"Đã cập nhật thông tin ca sĩ '{name}' thành công."})
    except Exception as e:
        LOGGER.error(f"[UPDATE ARTIST] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@router.post("/api/music/artists/auto-fetch")
async def auto_fetch_artists_metadata(_: bool = Depends(require_auth)):
    """
    Tiến trình quét ngầm tự động tìm & lưu ảnh chân dung HD, fanart, bio và thể loại cho toàn bộ ca sĩ trong thư viện
    kết hợp 4 nguồn: Deezer, TheAudioDB, Last.fm và Apple Music
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
            if not art_name or art_name.lower() in ["unknown", "unknown artist", "va", "various artists"]:
                continue
                
            slug = art_name.lower().strip()
            existing = await coll.find_one({"_id": slug})
            if existing and existing.get("avatar_url") and existing.get("bio"):
                continue  # Đã có đầy đủ ảnh và tiểu sử
                
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
                
                # 4. Gom thể loại
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
                
                if avatar_url or bio or genres:
                    doc = {
                        "name": art_name,
                        "avatar_url": avatar_url,
                        "banner_url": banner_url or avatar_url,
                        "bio": bio,
                        "genres": genres[:5],
                        "fans_count": avatar_match.get("fans_count", 0) if avatar_match else 0,
                        "source": "Deezer + TheAudioDB + Last.fm",
                        "updated_at": time.time()
                    }
                    await coll.update_one({"_id": slug}, {"$set": doc}, upsert=True)
                    updated_count += 1
            
            # Nghỉ nhẹ 100ms tránh rate-limit
            import asyncio
            await asyncio.sleep(0.1)

        return JSONResponse(content={
            "status": "success", 
            "count": updated_count, 
            "message": f"Đã tự động tải và cập nhật ảnh chân dung HD, Fanart & Tiểu sử cho {updated_count} ca sĩ!"
        })
    except Exception as e:
        LOGGER.error(f"[AUTO FETCH ARTISTS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ==============================================================================
# REAL-TIME SYNCED LYRICS (LRCLIB & CUSTOM LRC ENGINE)
# ==============================================================================

_lyrics_memory_cache: Dict[str, dict] = {}
_LYRICS_CACHE_TTL = 86400 * 7  # 7 days

def _split_artist_title(raw_text: str):
    """Tách Tên Ca Sĩ - Tên Bài Hát từ chuỗi tổng hợp (vd: Sơn Tùng - Chúng Ta Của Hiện Tại)"""
    if not raw_text:
        return "", ""
    t = raw_text.strip()
    t = re.sub(r'^\s*\d+[\s\.\-_]+', '', t)
    t = re.sub(r'\.(flac|mp3|m4a|wav|aac|ogg)$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)', '', t, flags=re.IGNORECASE)
    
    # Thử tách theo " - " hoặc " – " hoặc " — "
    for sep in (' - ', ' – ', ' — ', ' // '):
        if sep in t:
            parts = t.split(sep, 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            if p1 and p2:
                return p1, p2
    return "", t.strip()

def _clean_track_title_for_lyrics(title: str) -> str:
    """Làm sạch tên bài hát để tăng tỷ lệ tìm kiếm chính xác trên LRCLIB"""
    if not title:
        return ""
    p_artist, p_title = _split_artist_title(title)
    t = p_title if p_title else title
    t = re.sub(r'^\s*\d+[\s\.\-_]+', '', t)
    t = re.sub(r'\.(flac|mp3|m4a|wav|aac|ogg)$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _clean_artist_name_for_lyrics(artist: str, raw_title: str = "") -> str:
    if artist and artist.lower() not in ("unknown", "various artists", "xtapo music", "chưa rõ", "none"):
        a = re.sub(r'\[.*?\]', '', artist)
        a = re.sub(r'\s+', ' ', a).strip()
        return a
    # Thử lấy artist từ raw_title nếu raw_title có dạng "Artist - Title"
    p_artist, _ = _split_artist_title(raw_title)
    if p_artist and p_artist.lower() not in ("unknown", "various artists", "xtapo music", "chưa rõ", "none"):
        return p_artist
    return ""

@router.get("/api/music/lyrics")
async def get_realtime_lyrics(
    track_name: str = Query(..., description="Tên bài hát"),
    artist_name: Optional[str] = Query(None, description="Tên ca sĩ / nghệ sĩ"),
    album_name: Optional[str] = Query(None, description="Tên album"),
    duration: Optional[str] = Query(None, description="Thời lượng tính bằng giây"),
    force_refresh: Optional[bool] = Query(False, description="Bỏ qua cache")
):
    """
    Lấy lời bài hát đồng bộ từng giây (Synced Lyrics .LRC) từ LRCLIB.
    Tự động thử nhiều chiến lược: Exact Match -> Search Cleaned Title -> Fuzzy Search.
    """
    parsed_duration: Optional[float] = None
    if duration:
        try:
            val = float(str(duration).strip())
            if val > 0:
                parsed_duration = val
        except (ValueError, TypeError):
            parsed_duration = None
    duration = parsed_duration
    cleaned_track = _clean_track_title_for_lyrics(track_name)
    cleaned_artist = _clean_artist_name_for_lyrics(artist_name or "", track_name)
    
    cache_key = f"{cleaned_track.lower()}__{cleaned_artist.lower()}"
    
    # 1. Kiểm tra cache RAM
    if not force_refresh and cache_key in _lyrics_memory_cache:
        cached_entry = _lyrics_memory_cache[cache_key]
        if time.time() - cached_entry.get("_cached_at", 0) < _LYRICS_CACHE_TTL:
            return JSONResponse(content=cached_entry["data"])
    
    # 2. Kiểm tra Database MongoDB nếu đã lưu tùy chỉnh
    if db is not None and not force_refresh:
        try:
            coll = db.get_collection("music_custom_lyrics")
            if coll is not None:
                doc = await coll.find_one({"_id": cache_key})
                if doc:
                    doc_data = {
                        "status": "success",
                        "id": doc.get("id", 0),
                        "track_name": doc.get("track_name", cleaned_track),
                        "artist_name": doc.get("artist_name", cleaned_artist),
                        "synced_lyrics": doc.get("synced_lyrics", ""),
                        "plain_lyrics": doc.get("plain_lyrics", ""),
                        "instrumental": doc.get("instrumental", False),
                        "is_custom": True,
                        "source": "custom_db"
                    }
                    _lyrics_memory_cache[cache_key] = {"data": doc_data, "_cached_at": time.time()}
                    return JSONResponse(content=doc_data)
        except Exception as e:
            LOGGER.debug(f"[Lyrics DB Check] Note: {e}")

    headers = {
        "User-Agent": "XTAPO-Music-Player/2.0 (https://github.com/xtapo/Telegram-Stremio)"
    }
    
    async with httpx.AsyncClient(timeout=9.0, follow_redirects=True) as client:
        # A1: Thử /api/get exact match (with duration)
        if duration and duration > 0:
            try:
                get_params = {"track_name": cleaned_track, "duration": int(duration)}
                if cleaned_artist: get_params["artist_name"] = cleaned_artist
                if album_name and album_name.strip(): get_params["album_name"] = album_name.strip()
                resp = await client.get("https://lrclib.net/api/get", params=get_params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("syncedLyrics"):
                        result = {
                            "status": "success",
                            "id": data.get("id"),
                            "track_name": data.get("trackName") or cleaned_track,
                            "artist_name": data.get("artistName") or cleaned_artist,
                            "album_name": data.get("albumName") or album_name,
                            "duration": data.get("duration"),
                            "synced_lyrics": data.get("syncedLyrics") or "",
                            "plain_lyrics": data.get("plainLyrics") or "",
                            "instrumental": data.get("instrumental", False),
                            "source": "lrclib_exact"
                        }
                        _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                        return JSONResponse(content=result)
            except Exception as e:
                LOGGER.debug(f"[LRCLIB Exact Duration] Note: {e}")

        # A2: Thử /api/get exact match (without duration)
        try:
            get_params = {"track_name": cleaned_track}
            if cleaned_artist: get_params["artist_name"] = cleaned_artist
            if album_name and album_name.strip(): get_params["album_name"] = album_name.strip()
            resp = await client.get("https://lrclib.net/api/get", params=get_params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("syncedLyrics") or data.get("plainLyrics"):
                    result = {
                        "status": "success",
                        "id": data.get("id"),
                        "track_name": data.get("trackName") or cleaned_track,
                        "artist_name": data.get("artistName") or cleaned_artist,
                        "album_name": data.get("albumName") or album_name,
                        "duration": data.get("duration"),
                        "synced_lyrics": data.get("syncedLyrics") or "",
                        "plain_lyrics": data.get("plainLyrics") or "",
                        "instrumental": data.get("instrumental", False),
                        "source": "lrclib_exact_nodur"
                    }
                    _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                    return JSONResponse(content=result)
        except Exception as e:
            LOGGER.debug(f"[LRCLIB Exact NoDur] Note: {e}")

        # B: Thu thập kết quả từ nhiều truy vấn tìm kiếm
        search_queries = []
        if cleaned_artist:
            search_queries.append(f"{cleaned_track} {cleaned_artist}")
            search_queries.append(f"{cleaned_artist} {cleaned_track}")
        search_queries.append(cleaned_track)

        collected_items = []
        for q_str in search_queries:
            try:
                resp = await client.get("https://lrclib.net/api/search", params={"q": q_str}, headers=headers)
                if resp.status_code == 200:
                    items = resp.json()
                    if isinstance(items, list) and len(items) > 0:
                        collected_items.extend(items)
                        # Nếu đã có ít nhất 1 item có syncedLyrics, không cần search thêm
                        if any(it.get("syncedLyrics") for it in items):
                            break
            except Exception as e:
                LOGGER.debug(f"[LRCLIB Search '{q_str}'] Note: {e}")

        if collected_items:
            # Chấm điểm và xếp hạng kết quả tốt nhất
            def score_item(item):
                s = 0
                has_synced = bool(item.get("syncedLyrics"))
                if has_synced:
                    s += 1000  # Ưu tiên tuyệt đối lời có đồng bộ
                
                # Khớp tên bài hát
                i_name = (item.get("trackName") or "").lower()
                if i_name == cleaned_track.lower():
                    s += 300
                elif cleaned_track.lower() in i_name or i_name in cleaned_track.lower():
                    s += 150
                
                # Khớp tên ca sĩ
                if cleaned_artist:
                    i_art = (item.get("artistName") or "").lower()
                    if i_art == cleaned_artist.lower():
                        s += 250
                    elif cleaned_artist.lower() in i_art or i_art in cleaned_artist.lower():
                        s += 100
                
                # Khớp thời lượng (gần nhất)
                if duration and duration > 0 and item.get("duration"):
                    diff = abs(item["duration"] - duration)
                    if diff <= 3:
                        s += 200
                    elif diff <= 8:
                        s += 100
                    elif diff <= 20:
                        s += 40
                    else:
                        s -= min(100, int(diff * 2))
                return s

            collected_items.sort(key=score_item, reverse=True)
            best_match = collected_items[0]

            synced = best_match.get("syncedLyrics") or ""
            plain = best_match.get("plainLyrics") or ""

            if synced:
                result = {
                    "status": "success",
                    "id": best_match.get("id"),
                    "track_name": best_match.get("trackName") or cleaned_track,
                    "artist_name": best_match.get("artistName") or cleaned_artist,
                    "album_name": best_match.get("albumName") or album_name,
                    "duration": best_match.get("duration"),
                    "synced_lyrics": synced,
                    "plain_lyrics": plain,
                    "instrumental": best_match.get("instrumental", False),
                    "source": "lrclib_ranked_search"
                }
                _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                return JSONResponse(content=result)

        # 4. Chiến lược D: Thử Netease Cloud Music (163 Music - Siêu mạnh về V-Pop, K-Pop, C-Pop & Quốc Tế)
        try:
            netease_query = f"{cleaned_track} {cleaned_artist}".strip()
            netease_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://music.163.com/"
            }
            n_resp = await client.post(
                "https://music.163.com/api/cloudsearch/pc",
                data={"s": netease_query, "type": 1, "limit": 4},
                headers=netease_headers
            )
            if n_resp.status_code == 200:
                n_data = n_resp.json()
                n_songs = n_data.get("result", {}).get("songs", [])
                for song in n_songs:
                    sid = song.get("id")
                    if not sid:
                        continue
                    r_lrc = await client.get(
                        "https://music.163.com/api/song/lyric",
                        params={"os": "pc", "id": sid, "lv": -1, "kv": -1, "tv": -1},
                        headers=netease_headers
                    )
                    if r_lrc.status_code == 200:
                        l_json = r_lrc.json()
                        raw_lrc = l_json.get("lrc", {}).get("lyric", "").strip()
                        if raw_lrc:
                            has_synced = bool(re.search(r'\[\d{1,2}:\d{1,2}', raw_lrc))
                            artist_str = ""
                            if song.get("ar") and isinstance(song["ar"], list) and len(song["ar"]) > 0:
                                artist_str = song["ar"][0].get("name", "")
                            
                            netease_result = {
                                "status": "success",
                                "id": sid,
                                "track_name": song.get("name") or cleaned_track,
                                "artist_name": artist_str or cleaned_artist,
                                "album_name": (song.get("al") or {}).get("name") or album_name,
                                "duration": int(song.get("dt", 0) / 1000) if song.get("dt") else None,
                                "synced_lyrics": raw_lrc if has_synced else "",
                                "plain_lyrics": "" if has_synced else raw_lrc,
                                "instrumental": False,
                                "source": "netease_cloud"
                            }
                            _lyrics_memory_cache[cache_key] = {"data": netease_result, "_cached_at": time.time()}
                            return JSONResponse(content=netease_result)
        except Exception as e:
            LOGGER.debug(f"[Netease Lyrics Engine] Note: {e}")

        # 5. Nếu chỉ có plain lyrics từ LRCLIB
        if collected_items and collected_items[0].get("plainLyrics"):
            best_p = collected_items[0]
            result = {
                "status": "success",
                "id": best_p.get("id"),
                "track_name": best_p.get("trackName") or cleaned_track,
                "artist_name": best_p.get("artistName") or cleaned_artist,
                "album_name": best_p.get("albumName") or album_name,
                "duration": best_p.get("duration"),
                "synced_lyrics": "",
                "plain_lyrics": best_p.get("plainLyrics") or "",
                "instrumental": best_p.get("instrumental", False),
                "source": "lrclib_plain"
            }
            _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
            return JSONResponse(content=result)

    # Không tìm thấy lời bài hát
    not_found_res = {
        "status": "not_found",
        "track_name": cleaned_track,
        "artist_name": cleaned_artist,
        "synced_lyrics": "",
        "plain_lyrics": "",
        "message": f"Chưa có sẵn lời bài hát cho '{cleaned_track}'. Bạn có thể dán file .lrc thủ công!"
    }
    _lyrics_memory_cache[cache_key] = {"data": not_found_res, "_cached_at": time.time()}
    return JSONResponse(status_code=404, content=not_found_res)


@router.get("/api/music/lyrics/search")
async def search_lyrics_multi_source(
    track_name: str = Query(..., description="Tên bài hát cần tìm"),
    artist_name: Optional[str] = Query(None, description="Tên ca sĩ"),
    provider: Optional[str] = Query("all", description="Nguồn: all | lrclib | netease")
):
    """Tìm kiếm lời bài hát trực tuyến từ đa nguồn (LRCLIB Quốc Tế + Netease 163 V-Pop/Châu Á)"""
    cleaned_track = _clean_track_title_for_lyrics(track_name)
    cleaned_artist = _clean_artist_name_for_lyrics(artist_name or "", track_name)
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        # 1. Tìm trên LRCLIB
        if provider in ("all", "lrclib"):
            try:
                q_str = f"{cleaned_track} {cleaned_artist}".strip()
                resp = await client.get("https://lrclib.net/api/search", params={"q": q_str}, headers=headers)
                if resp.status_code == 200:
                    items = resp.json()
                    if isinstance(items, list):
                        for it in items[:6]:
                            synced = it.get("syncedLyrics") or ""
                            plain = it.get("plainLyrics") or ""
                            if synced or plain:
                                results.append({
                                    "id": f"lrclib_{it.get('id')}",
                                    "track_name": it.get("trackName") or cleaned_track,
                                    "artist_name": it.get("artistName") or "",
                                    "album_name": it.get("albumName") or "",
                                    "duration": it.get("duration"),
                                    "is_synced": bool(synced),
                                    "synced_lyrics": synced,
                                    "plain_lyrics": plain,
                                    "source": "LRCLIB Quốc Tế"
                                })
            except Exception as e:
                LOGGER.debug(f"[Search LRCLIB] Error: {e}")

        # 2. Tìm trên Netease 163 Cloud Music (Cực mạnh cho Nhạc Việt & Châu Á)
        if provider in ("all", "netease"):
            try:
                n_query = f"{cleaned_track} {cleaned_artist}".strip()
                n_headers = headers.copy()
                n_headers["Referer"] = "https://music.163.com/"
                n_resp = await client.post(
                    "https://music.163.com/api/cloudsearch/pc",
                    data={"s": n_query, "type": 1, "limit": 6},
                    headers=n_headers
                )
                if n_resp.status_code == 200:
                    n_data = n_resp.json()
                    songs = n_data.get("result", {}).get("songs", [])
                    for song in songs:
                        sid = song.get("id")
                        if not sid:
                            continue
                        r_l = await client.get(
                            "https://music.163.com/api/song/lyric",
                            params={"os": "pc", "id": sid, "lv": -1, "kv": -1, "tv": -1},
                            headers=n_headers
                        )
                        if r_l.status_code == 200:
                            l_json = r_l.json()
                            raw_lrc = l_json.get("lrc", {}).get("lyric", "").strip()
                            if raw_lrc:
                                has_synced = bool(re.search(r'\[\d{1,2}:\d{1,2}', raw_lrc))
                                ar_name = ""
                                if song.get("ar") and isinstance(song["ar"], list) and len(song["ar"]) > 0:
                                    ar_name = song["ar"][0].get("name", "")
                                results.append({
                                    "id": f"netease_{sid}",
                                    "track_name": song.get("name") or cleaned_track,
                                    "artist_name": ar_name or cleaned_artist,
                                    "album_name": (song.get("al") or {}).get("name") or "",
                                    "duration": int(song.get("dt", 0) / 1000) if song.get("dt") else None,
                                    "is_synced": has_synced,
                                    "synced_lyrics": raw_lrc if has_synced else "",
                                    "plain_lyrics": "" if has_synced else raw_lrc,
                                    "source": "Netease 163"
                                })
            except Exception as e:
                LOGGER.debug(f"[Search Netease] Error: {e}")

    # Ưu tiên mục có synced lyrics lên đầu
    results.sort(key=lambda x: (1 if x["is_synced"] else 0), reverse=True)
    return JSONResponse(content={"status": "success", "count": len(results), "items": results})


@router.post("/api/music/lyrics/save")
async def save_custom_lyrics(
    request: Request,
    user: Optional[dict] = Depends(get_current_user)
):
    """Lưu lời bài hát do người dùng chỉnh sửa hoặc dán file .lrc thủ công"""
    try:
        data = await request.json()
        track_name = data.get("track_name", "").strip()
        artist_name = data.get("artist_name", "").strip()
        synced_lyrics = data.get("synced_lyrics", "").strip()
        plain_lyrics = data.get("plain_lyrics", "").strip()
        
        if not track_name:
            raise HTTPException(status_code=400, detail="Thiếu tên bài hát")
            
        cleaned_track = _clean_track_title_for_lyrics(track_name)
        cleaned_artist = _clean_artist_name_for_lyrics(artist_name)
        cache_key = f"{cleaned_track.lower()}__{cleaned_artist.lower()}"
        
        doc_data = {
            "status": "success",
            "track_name": cleaned_track,
            "artist_name": cleaned_artist,
            "synced_lyrics": synced_lyrics,
            "plain_lyrics": plain_lyrics,
            "instrumental": data.get("instrumental", False),
            "is_custom": True,
            "source": "custom_saved"
        }
        
        # Cập nhật cache RAM
        _lyrics_memory_cache[cache_key] = {"data": doc_data, "_cached_at": time.time()}
        
        # Cập nhật Database nếu có
        if db is not None:
            coll = db.get_collection("music_custom_lyrics")
            if coll is not None:
                await coll.update_one(
                    {"_id": cache_key},
                    {"$set": {
                        "track_name": cleaned_track,
                        "artist_name": cleaned_artist,
                        "synced_lyrics": synced_lyrics,
                        "plain_lyrics": plain_lyrics,
                        "updated_by": user.get("username") if user else "anonymous",
                        "updated_at": time.time()
                    }},
                    upsert=True
                )
                
        return JSONResponse(content={
            "status": "success", 
            "message": "Đã lưu lời bài hát .lrc thành công!",
            "data": doc_data
        })
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"[SAVE LYRICS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


# ==============================================================================
# 10. GOOGLE DRIVE MUSIC UPLOADER (USER SESSION & BOT)
# ==============================================================================

@router.get("/api/music/uploader/client-status")
async def get_uploader_client_status(_: bool = Depends(require_auth)):
    """Kiểm tra trạng thái các User Sessions và Telegram Bot Client phục vụ upload tốc độ cao"""
    from Backend.helper.session_auth import get_multi_session_status
    multi_status = await get_multi_session_status()
    userbot_connected = bool(botmod.Userbot and getattr(botmod.Userbot, "is_connected", False)) or multi_status["active_sessions"] > 0
    stored_session_exists = multi_status["total_sessions"] > 0
    bot_connected = bool(getattr(StreamBot, "is_connected", False))

    return JSONResponse(content={
        "status": "success",
        "userbot_connected": userbot_connected,
        "stored_session_exists": stored_session_exists,
        "active_userbot_count": multi_status["active_sessions"],
        "total_userbot_count": multi_status["total_sessions"],
        "multi_sessions": multi_status["sessions"],
        "bot_connected": bot_connected,
        "active_mode": "user_session" if userbot_connected or stored_session_exists else "bot",
        "speed_tier": f"⚡ Tối đa ({multi_status['active_sessions']} User Sessions hoạt động)" if userbot_connected else "🤖 Tiêu chuẩn (Telegram Bot API)"
    })


@router.post("/api/music/gdrive-upload/start")
async def start_gdrive_upload(payload: dict, _: bool = Depends(require_auth)):
    """Khởi chạy tiến trình tải nhạc từ Google Drive và upload lên kênh Telegram"""
    url = payload.get("url", "").strip()
    channel_id = payload.get("channel_id", "").strip()
    default_artist = payload.get("default_artist", "").strip()
    default_album = payload.get("default_album", "").strip()
    auto_scrape = payload.get("auto_scrape", True)
    send_as_document = payload.get("send_as_document", False)

    if not url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng nhập URL Google Drive hoặc link tải."})
    if not channel_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng chọn Kênh Telegram đích."})

    import importlib
    import Backend.helper.gdrive_uploader as gdu
    try:
        importlib.reload(gdu)
    except Exception:
        pass
    gdrive_upload_manager = gdu.gdrive_upload_manager
    res = await gdrive_upload_manager.start(
        url=url,
        target_channel_id=channel_id,
        default_artist=default_artist,
        default_album=default_album,
        auto_scrape=auto_scrape,
        send_as_document=send_as_document
    )

    if not res.get("ok"):
        return JSONResponse(status_code=409, content={"status": "error", "message": res.get("message")})

    return JSONResponse(content={
        "status": "success",
        "message": res.get("message"),
        "client_type": res.get("client_type"),
        "data": gdrive_upload_manager.get_status()
    })


@router.get("/api/music/gdrive-upload/status")
async def get_gdrive_upload_status():
    """Lấy trạng thái và tiến trình upload thời gian thực"""
    from Backend.helper.gdrive_uploader import gdrive_upload_manager
    return JSONResponse(content={
        "status": "success",
        "data": gdrive_upload_manager.get_status()
    })


@router.post("/api/music/gdrive-upload/cancel")
async def cancel_gdrive_upload(_: bool = Depends(require_auth)):
    """Hủy tiến trình upload từ Google Drive"""
    from Backend.helper.gdrive_uploader import gdrive_upload_manager
    res = await gdrive_upload_manager.cancel()
    return JSONResponse(content={
        "status": "success" if res.get("ok") else "error",
        "message": res.get("message")
    })



