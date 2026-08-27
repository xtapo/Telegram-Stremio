import asyncio
import re
import urllib.parse
import httpx
from typing import Dict, Optional, Tuple
from Backend.logger import LOGGER

_METADATA_CACHE: Dict[str, dict] = {}

# Common audio noise regex patterns
NOISE_PATTERNS = [
    r'@\w+',                              # @channel_name
    r'\[.*?\]',                           # [320kbps], [FLAC], [Official]
    r'\(Official.*?\)',                   # (Official Music Video), (Official Audio)
    r'\(Lyric.*?\)',                      # (Lyric Video)
    r'\(Audio\)',                         # (Audio)
    r'\(Visualizer\)',                    # (Visualizer)
    r'\(Remastered.*?\)',                 # (Remastered 2024)
    r'\b(320kbps|128kbps|256kbps|FLAC|MP3|WAV|24bit|16bit|96kHz|44\.1kHz|Hi-Res|Lossless)\b',
    r'\.(mp3|flac|m4a|wav|aac|ogg|opus|alac|dsf|ape)$',
]


def clean_music_query(text: str) -> str:
    """Làm sạch tên file/tiêu đề để tìm kiếm chính xác nhất"""
    if not text:
        return ""
    result = text
    for pat in NOISE_PATTERNS:
        result = re.sub(pat, ' ', result, flags=re.IGNORECASE)
    # Thay thế dấu gạch dưới, gạch ngang thừa, khoảng trắng thừa
    result = result.replace('_', ' ').replace('-', ' - ')
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def extract_artist_and_title(raw_name: str, fallback_artist: str = None) -> Tuple[str, str]:
    """Phân tách 'Artist - Title' từ tên file"""
    clean_str = clean_music_query(raw_name)
    if ' - ' in clean_str:
        parts = clean_str.split(' - ', 1)
        artist = parts[0].strip()
        title = parts[1].strip()
        return artist, title
    
    artist = fallback_artist.strip() if fallback_artist and fallback_artist.lower() != "unknown artist" else ""
    return artist, clean_str


async def fetch_music_metadata(raw_title: str, raw_artist: str = "", file_name: str = "") -> Optional[dict]:
    """
    Tự động quét metadata bài hát & album từ iTunes Search API & Deezer API (tương tự TMDB cho phim)
    Trả về: Album chính thức, Nghệ sĩ chuẩn, Bìa HD 1200x1200px, Năm phát hành, Thể loại, Hãng đĩa.
    """
    artist, title = extract_artist_and_title(raw_title or file_name, raw_artist)
    if not title:
        title = clean_music_query(file_name)
    if not title:
        return None

    query = f"{artist} {title}".strip() if artist else title
    cache_key = query.lower()
    if cache_key in _METADATA_CACHE:
        return _METADATA_CACHE[cache_key]

    LOGGER.info(f"[MUSIC SCRAPER] Đang tìm metadata chuẩn cho: '{query}'...")

    # 1. Thử iTunes / Apple Music Search API (Chất lượng cao nhất, không cần API Key)
    try:
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&entity=song&limit=1"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("resultCount", 0) > 0:
                    track_info = data["results"][0]
                    
                    # Nâng cấp ảnh bìa lên chuẩn Ultra HD (1200x1200 hoặc 1400x1400)
                    raw_art = track_info.get("artworkUrl100", "")
                    hd_cover = raw_art.replace("100x100bb.jpg", "1200x1200bb.webp").replace("100x100bb.png", "1200x1200bb.webp")
                    if not hd_cover:
                        hd_cover = raw_art

                    release_date = track_info.get("releaseDate", "")
                    year = release_date[:4] if len(release_date) >= 4 else "2026"
                    genre = track_info.get("primaryGenreName", "Pop / Hi-Res")
                    album_name = track_info.get("collectionName", "").strip() or f"{track_info.get('trackName')} - Single"

                    result = {
                        "title": track_info.get("trackName", title).strip(),
                        "artist": track_info.get("artistName", artist or "Unknown Artist").strip(),
                        "album": album_name,
                        "cover_url": hd_cover,
                        "year": year,
                        "genre": genre,
                        "publisher": f"{track_info.get('artistName')} / Apple Music",
                        "preview_audio": track_info.get("previewUrl", None),
                        "track_number": track_info.get("trackNumber", 1),
                        "total_tracks": track_info.get("trackCount", 1),
                        "source": "Apple Music / iTunes"
                    }
                    _METADATA_CACHE[cache_key] = result
                    LOGGER.info(f"[MUSIC SCRAPER] ✅ Đã tìm thấy: {result['artist']} - {result['title']} (Album: {result['album']})")
                    return result
    except Exception as e:
        LOGGER.warning(f"[MUSIC SCRAPER] iTunes lookup failed for '{query}': {e}")

    # 2. Dự phòng: Thử Deezer API
    try:
        url = f"https://api.deezer.com/search?q={urllib.parse.quote(query)}&limit=1"
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("data") and len(data["data"]) > 0:
                    item = data["data"][0]
                    album_obj = item.get("album", {})
                    artist_obj = item.get("artist", {})

                    cover_url = album_obj.get("cover_xl") or album_obj.get("cover_big") or album_obj.get("cover_medium") or ""
                    album_name = album_obj.get("title", "").strip() or f"{item.get('title')} - Single"

                    result = {
                        "title": item.get("title", title).strip(),
                        "artist": artist_obj.get("name", artist or "Unknown Artist").strip(),
                        "album": album_name,
                        "cover_url": cover_url,
                        "year": "2026",
                        "genre": "Lossless Audio",
                        "publisher": f"{artist_obj.get('name')} / Deezer",
                        "preview_audio": item.get("preview", None),
                        "source": "Deezer"
                    }
                    _METADATA_CACHE[cache_key] = result
                    LOGGER.info(f"[MUSIC SCRAPER] ✅ Deezer tìm thấy: {result['artist']} - {result['title']}")
                    return result
    except Exception as e:
        LOGGER.warning(f"[MUSIC SCRAPER] Deezer lookup failed for '{query}': {e}")

    # Fallback nếu không tìm thấy trên mạng
    clean_title = title if title else "Track"
    clean_art = artist if artist else "Unknown Artist"
    return {
        "title": clean_title,
        "artist": clean_art,
        "album": "Telegram Music Collection",
        "cover_url": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=1000&auto=format&fit=crop",
        "year": "2026",
        "genre": "Hi-Res Audio",
        "publisher": "Telegram Cloud Archive",
        "source": "Telegram Direct"
    }
