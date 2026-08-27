import asyncio
import io
import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple

import httpx
from shazamlite import ShazamAsync, NoMatch, BadData

from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, Userbot, USERBOT_CLIENT_INDEX, multi_clients
from Backend.fastapi.routes.stream_routes import _get_streamer


_GENERIC_PATTERNS = [
    r'^\s*track[\s_.-]*\d+\b',          # track_01, track 1, track-02
    r'^\s*audio[\s_.-]*\d+\b',          # audio_123, audio 01
    r'^\s*song[\s_.-]*\d+\b',           # song_1, song 02
    r'^\s*file[\s_.-]*\d+\b',           # file_01
    r'^\s*\d{1,3}\b$',                  # 01, 02, 10
    r'^\s*untitled\b',                  # untitled, untitled 1
    r'^\s*unknown\b',                   # unknown, unknown track
    r'^\s*noname\b',                    # noname
    r'^\s*cd\d+[\s_.-]*track[\s_.-]*\d+\b', # cd1_track01
    r'^\s*disc\d+[\s_.-]*\d+\b',        # disc1_01
    r'^\s*bai[\s_.-]*\d+\b',            # bai_01, bai 1
]


def is_generic_track_name(title: str, artist: str = "") -> bool:
    """
    Kiểm tra xem tên bài hát có phải là tên generic / mất thông tin hay không.
    Ví dụ: track_01.flac, audio_123.mp3, 01.mp3, Untitled, Unknown Artist...
    """
    if not title:
        return True
    
    t = title.strip().lower()
    # Loại bỏ phần mở rộng nếu còn sót
    t = re.sub(r'\.(mp3|flac|m4a|wav|aac|ogg|opus|alac|dsf|ape)$', '', t)
    
    if not t or len(t) <= 1:
        return True

    for pat in _GENERIC_PATTERNS:
        if re.search(pat, t, re.IGNORECASE):
            return True

    # Nếu artist rỗng hoặc là Unknown Artist và title chỉ là số hoặc từ ngắn
    a = (artist or "").strip().lower()
    if not a or a in ["unknown artist", "unknown", "va", "various artists", "telegram", "lossless"]:
        if re.match(r'^\d+$', t) or len(t) <= 3:
            return True

    return False


def convert_audio_snippet_to_wav(raw_bytes: bytes, max_seconds: float = 12.0) -> bytes:
    """
    Sử dụng FFmpeg chuyển đổi một đoạn audio bất kỳ (FLAC, MP3, WAV, M4A, ALAC, AAC, OGG, OPUS, DSF, APE)
    sang định dạng 16kHz mono PCM WAV tương thích 100% với Shazam Signature Generator.
    """
    if not raw_bytes:
        raise ValueError("Empty audio bytes")

    # Command FFmpeg: đọc từ stdin (pipe:0), cắt tối đa max_seconds, sample rate 16000Hz, mono (1 kênh), xuất WAV (pipe:1)
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", "pipe:0",
        "-t", str(max_seconds),
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        "pipe:1"
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=raw_bytes,
            capture_output=True,
            timeout=15.0
        )
        if proc.returncode != 0 or not proc.stdout:
            err_msg = proc.stderr.decode("utf-8", errors="ignore") if proc.stderr else "Unknown FFmpeg error"
            LOGGER.warning(f"[AUDIO FINGERPRINT] FFmpeg conversion failed: {err_msg}")
            raise RuntimeError(f"FFmpeg error: {err_msg}")
        
        return proc.stdout
    except subprocess.TimeoutExpired:
        LOGGER.error("[AUDIO FINGERPRINT] FFmpeg conversion timed out")
        raise TimeoutError("FFmpeg process timed out")


async def recognize_audio_bytes(raw_bytes: bytes, max_seconds: float = 12.0) -> Optional[dict]:
    """
    Nhận diện bài hát từ dữ liệu âm thanh (bytes) qua Shazam Audio Fingerprinting.
    
    Returns:
        dict chứa:
            - title: Tên bài hát gốc
            - artist: Ca sĩ / Nghệ sĩ gốc
            - album: Tên album
            - cover_url: Ảnh bìa HD
            - year: Năm phát hành
            - genre: Thể loại
            - apple_music_url: Link Apple Music
            - spotify_uri: Spotify URI
            - isrc: Mã ISRC
            - source: 'Shazam Audio Fingerprint'
        hoặc None nếu không nhận diện được (NoMatch)
    """
    if not raw_bytes:
        return None

    try:
        wav_bytes = convert_audio_snippet_to_wav(raw_bytes, max_seconds=max_seconds)
    except Exception as e:
        LOGGER.warning(f"[AUDIO FINGERPRINT] Could not convert audio snippet: {e}")
        return None

    try:
        shazam = ShazamAsync()
        track = await shazam.recognize(wav_bytes)
        
        if not track or not track.title:
            return None

        # Trích xuất thông tin album
        album_name = ""
        album_cover = ""
        if track.album:
            album_name = track.album.title or track.album.name or ""
            album_cover = track.album.coverart or ""

        # Trích xuất ảnh bìa chất lượng cao nhất
        cover_url = ""
        if track.images:
            # Sắp xếp ảnh theo kích thước lớn nhất
            sorted_imgs = sorted(track.images, key=lambda img: (img.width or 0) * (img.height or 0), reverse=True)
            if sorted_imgs:
                cover_url = sorted_imgs[0].url or ""
        
        if not cover_url and album_cover:
            cover_url = album_cover

        # Nâng cấp ảnh bìa Apple Music lên độ phân giải cao 1200x1200 nếu có
        if cover_url and "mzstatic.com" in cover_url:
            cover_url = re.sub(r'\d+x\d+bb\.(jpg|png|webp)', '1200x1200bb.webp', cover_url)

        # Trích xuất nghệ sĩ
        artist_name = track.subtitle or ""
        if not artist_name and track.artists:
            artist_name = ", ".join([a.name for a in track.artists if a.name])

        # Trích xuất năm phát hành & thể loại từ metadata sections
        year = time.strftime("%Y")
        genre = "Pop / Hi-Res"
        publisher = artist_name or "Apple Music"

        if track.genres:
            genre = " / ".join(track.genres)

        if track.sections:
            for sec in track.sections:
                if sec.get("type") == "SONG":
                    metadata_list = sec.get("metadata", [])
                    for item in metadata_list:
                        item_title = item.get("title", "").lower()
                        item_text = item.get("text", "")
                        if "album" in item_title and not album_name:
                            album_name = item_text
                        elif "label" in item_title or "record" in item_title:
                            publisher = item_text
                        elif "released" in item_title or "year" in item_title:
                            match_yr = re.search(r'\b(19\d{2}|20\d{2})\b', item_text)
                            if match_yr:
                                year = match_yr.group(1)

        result = {
            "title": track.title.strip(),
            "artist": (artist_name or "Unknown Artist").strip(),
            "album": (album_name or f"{track.title.strip()} - Single").strip(),
            "cover_url": cover_url,
            "year": str(year),
            "genre": genre,
            "publisher": publisher,
            "apple_music_url": track.apple_music_url or "",
            "spotify_uri": track.spotify_uri or "",
            "isrc": track.isrc or "",
            "source": "Shazam Audio Fingerprint",
            "shazam_key": track.key or ""
        }
        
        LOGGER.info(f"[AUDIO FINGERPRINT] 🧠 Nhận diện thành công: {result['artist']} - {result['title']} (Album: {result['album']}, Năm: {result['year']})")
        return result

    except NoMatch:
        LOGGER.info("[AUDIO FINGERPRINT] Shazam: Không tìm thấy bài hát khớp với sóng âm này (NoMatch).")
        return None
    except BadData as bd:
        LOGGER.warning(f"[AUDIO FINGERPRINT] Shazam BadData: {bd}")
        return None
    except Exception as e:
        LOGGER.error(f"[AUDIO FINGERPRINT] Shazam recognition error: {e}", exc_info=True)
        return None


async def fetch_telegram_audio_sample(chat_id: int, msg_id: int, max_bytes: int = 1500000) -> Optional[bytes]:
    """
    Tải nhanh đoạn đầu (khoảng 1.5MB) của file nhạc từ Telegram để phục vụ nhận diện sóng âm.
    Không tải toàn bộ file 50-200MB, giúp nhận diện chỉ mất 1-2 giây.
    """
    # 1. Thử dùng ByteStreamer với Telegram Clients
    clients_to_try = []
    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
        clients_to_try.append((USERBOT_CLIENT_INDEX, botmod.Userbot))
    if multi_clients:
        for idx, cl in multi_clients.items():
            if (idx, cl) not in clients_to_try:
                clients_to_try.append((idx, cl))
    if StreamBot:
        clients_to_try.append((0, StreamBot))

    for c_idx, tg_client in clients_to_try:
        try:
            streamer = _get_streamer(tg_client, c_idx)
            file_id = await streamer.get_file_properties(chat_id=chat_id, message_id=msg_id)
            if not file_id:
                continue

            file_size = getattr(file_id, "file_size", 0) or 0
            read_len = min(file_size, max_bytes) if file_size > 0 else max_bytes

            # Tải chunk đầu tiên
            chunk_buffer = bytearray()
            async for chunk in streamer.yield_file(
                file_id=file_id,
                client_index=c_idx,
                offset=0,
                first_part_cut=0,
                last_part_cut=read_len,
                part_count=1,
                max_chunk_size=1024 * 1024,
                chat_id=chat_id,
                message_id=msg_id
            ):
                if chunk:
                    chunk_buffer.extend(chunk)
                    if len(chunk_buffer) >= max_bytes:
                        break

            if chunk_buffer:
                LOGGER.info(f"[AUDIO FINGERPRINT] Đã tải {len(chunk_buffer)} bytes sample từ Telegram {chat_id}/{msg_id}")
                return bytes(chunk_buffer)
        except Exception as e:
            LOGGER.debug(f"[AUDIO FINGERPRINT] Streamer client {c_idx} sample fetch failed: {e}")
            continue

    # 2. Fallback: Dùng Pyrogram direct download_media với in_memory
    for c_idx, tg_client in clients_to_try:
        try:
            msg = await tg_client.get_messages(chat_id, msg_id)
            media = getattr(msg, "audio", None) or getattr(msg, "document", None)
            if media:
                # Nếu file nhỏ < 5MB tải trực tiếp
                file_size = getattr(media, "file_size", 0) or 0
                if file_size <= 5 * 1024 * 1024:
                    buf = await tg_client.download_media(media, in_memory=True)
                    if buf and hasattr(buf, "getvalue"):
                        return buf.getvalue()
        except Exception:
            continue

    return None


async def recognize_telegram_audio_track(chat_id: int, msg_id: int) -> Optional[dict]:
    """
    Hàm tổng hợp: Đọc sample từ Telegram message và nhận diện sóng âm bằng Shazam.
    """
    sample_bytes = await fetch_telegram_audio_sample(chat_id=chat_id, msg_id=msg_id)
    if not sample_bytes:
        LOGGER.warning(f"[AUDIO FINGERPRINT] Không thể tải sample âm thanh cho bài {chat_id}/{msg_id}")
        return None

    return await recognize_audio_bytes(sample_bytes, max_seconds=12.0)
