import asyncio
import re
import urllib.parse
import httpx
from typing import Dict, Optional, Tuple, List
from Backend.logger import LOGGER

_METADATA_CACHE: Dict[str, dict] = {}


def token_similarity(str1: str, str2: str) -> float:
    """Tính độ tương đồng token giữa 2 chuỗi để chọn kết quả chính xác nhất"""
    if not str1 or not str2:
        return 0.0
    w1 = set(re.findall(r'[a-zA-Z0-9\u00C0-\u1EF9]+', str1.lower()))
    w2 = set(re.findall(r'[a-zA-Z0-9\u00C0-\u1EF9]+', str2.lower()))
    if not w1 or not w2:
        return 0.0
    intersection = w1.intersection(w2)
    return len(intersection) / max(len(w1), len(w2))


def clean_audio_filename(fn: str) -> str:
    """Làm sạch tên file/tiêu đề, loại bỏ các tag rác Telegram"""
    if not fn:
        return ""
    
    # 1. Bỏ phần mở rộng audio
    fn = re.sub(r'\.(mp3|flac|m4a|wav|aac|ogg|opus|alac|dsf|dff|dsd|ape|wma)$', '', fn, flags=re.IGNORECASE)
    
    # 2. Bỏ @channel username (ví dụ: @nhachot_2026, @MyChannel)
    fn = re.sub(r'@[^\s_.-]+[_\s.-]*', ' ', fn)
    
    # 3. Bỏ nội dung trong ngoặc vuông [320kbps], [FLAC 24-96], [Official], [NhacCuaTui]
    fn = re.sub(r'\[.*?\]', ' ', fn)
    
    # 4. Bỏ các tag trong ngoặc tròn như (Official Music Video), (Lyric Video), (Audio), (Remastered)
    fn = re.sub(r'\((Official|Lyric|Audio|Visualizer|Remastered|Album Version|Explicit|Video|Bonus|Deluxe|Live|MV|Full MV).*?\)', ' ', fn, flags=re.IGNORECASE)
    
    # 5. Bỏ các từ khóa chất lượng và định dạng audio thừa ở đuôi
    fn = re.sub(r'\b(320kbps|128kbps|256kbps|FLAC|MP3|WAV|DFF|DSF|DSD|24bit|16bit|96kHz|44\.1kHz|Hi-Res|Lossless|Kbps|HQ|HD|4K|1080p)\b', ' ', fn, flags=re.IGNORECASE)
    
    # 6. Chuẩn hóa khoảng trắng, dấu chấm, gạch dưới
    fn = fn.replace('_', ' ')
    fn = re.sub(r'\.+', ' ', fn)
    fn = re.sub(r'\s*-\s*', ' - ', fn)
    
    # 7. Bỏ số thứ tự bài hát ở đầu (ví dụ: "01. ", "01 - ", "01_", "1-02 ", "Track 01 ", "02 ")
    fn = re.sub(r'^\s*(\d{1,3}[\.\-_\s]+|\bTrack\s*\d+\b\s*[\.\-_\s]*|[A-D]\d+[\.\-_\s]+)', '', fn)
    
    fn = re.sub(r'\s+', ' ', fn).strip()
    return fn


_GARBAGE_KEYWORDS = {
    "admin", "download", "link", "join", "group", "channel", "pass", "password", 
    "zalo", "facebook", "telegram", "bot", "lossless", "flac", "mp3", "wav", 
    "320kbps", "192khz", "24bit", "16bit", "m4a", "dsd", "dsf", "hi-res", "hires",
    "http", "https", "t.me", "fshare", "drive", "youtube", "mediafire", "mega.nz"
}


def _is_valid_name(text: str, max_len: int = 60) -> bool:
    if not text:
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > max_len:
        return False
    if re.search(r'https?://|t\.me/|@[\w_]+|\b(?:fshare|drive\.google|mediafire)\b', t, re.I):
        return False
    words = set(re.findall(r'\b\w+\b', t.lower()))
    if words and words.issubset(_GARBAGE_KEYWORDS):
        return False
    return True


def extract_context_from_text(text: str) -> Tuple[str, str]:
    """
    Trích xuất tên Album và Ca Sĩ từ tin nhắn văn bản / caption một cách an toàn và nghiêm ngặt (Strict).
    Loại bỏ link rác, quảng cáo, và chỉ nhận diện khi có tiền tố hoặc cú pháp rõ ràng.
    """
    if not text:
        return "", ""
    
    # Loại bỏ link, username @, hashtag
    clean = re.sub(r'https?://\S+|t\.me/\S+|@[\w_]+|#\w+', '', text).strip()
    if not clean:
        return "", ""

    artist = ""
    album = ""

    # 1. Tìm theo tiền tố rõ ràng (Strict label match)
    artist_labels = r'Ca\s*s[ĩỹi]|Ngh[eệ]\s*s[ĩi]|Tr[iì]nh\s*b[aà]y|Artist|Singer|Performer'
    m_artist = re.search(rf'(?:{artist_labels})\s*[:\-–]\s*([^\n\r,;\|]+)', clean, re.IGNORECASE)
    if m_artist:
        candidate_artist = m_artist.group(1).strip()
        if _is_valid_name(candidate_artist, 50):
            artist = candidate_artist

    album_labels = r'Album|CD\s*\d*|Tuy[eể]n\s*t[aậ]p|[ĐD][ĩi]a\s*h[aá]t|Collection|Nh[aạ]c\s*tuy[eể]n'
    m_album = re.search(rf'(?:{album_labels})\s*[:\-–]\s*([^\n\r,;\|]+)', clean, re.IGNORECASE)
    if m_album:
        candidate_album = m_album.group(1).strip()
        if _is_valid_name(candidate_album, 60):
            album = candidate_album

    # 2. Dạng dòng đầu 'Artist - Album' ngắn gọn (< 70 ký tự)
    if not artist or not album:
        lines = [line.strip() for line in clean.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) <= 70:
                first_line = re.sub(r'^[^\w\s\u00C0-\u1EF9]+', '', first_line).strip()
                first_line = re.sub(r'\[.*?\]', '', first_line).strip()
                first_line = re.sub(r'\((?:19|20)\d{2}\)', '', first_line).strip()

                for sep in [' - ', ' – ', ' — ']:
                    if sep in first_line:
                        parts = first_line.split(sep)
                        if len(parts) >= 2:
                            p_art = parts[0].strip()
                            p_alb = parts[1].strip()
                            if not artist and _is_valid_name(p_art, 50):
                                artist = p_art
                            if not album and _is_valid_name(p_alb, 60):
                                album = p_alb
                        break

    return artist, album


def parse_artist_and_title(raw_title: str = "", raw_artist: str = "", raw_album: str = "", file_name: str = "", caption: str = "") -> Tuple[str, str, str]:
    """
    Trích xuất Artist, Title, Album ưu tiên dữ liệu gốc từ ID3 tag và File Name.
    """
    clean_fn = clean_audio_filename(file_name)
    clean_cap = clean_audio_filename(caption)
    clean_title = clean_audio_filename(raw_title)
    clean_artist = clean_audio_filename(raw_artist)
    
    # Loại bỏ số thứ tự track ở đầu (ví dụ: "01. ", "01 - ", "[01] ")
    def _strip_track_number(s: str) -> str:
        s = re.sub(r'^(?:\[?\d{1,3}\]?[\s.\-_–]+)', '', s).strip()
        return s

    if clean_title:
        clean_title = _strip_track_number(clean_title)
    if clean_fn:
        clean_fn = _strip_track_number(clean_fn)

    # Loại bỏ artist nếu là rác / bot / channel
    if clean_artist and ('@' in clean_artist or clean_artist.lower() in ["unknown artist", "unknown", "va", "various artists", "telegram", "lossless"]):
        clean_artist = ""

    # Trường hợp 1: ID3 Tag đã có đầy đủ Artist & Title hợp lệ (Ưu tiên 100%)
    if clean_artist and clean_title and clean_title.lower() != clean_artist.lower():
        return clean_artist, clean_title, raw_album or ""

    # Trường hợp 2: Tách từ File Name dạng "Artist - Title" hoặc "Title - Artist"
    target_str = clean_fn or clean_cap or clean_title
    for sep in [' - ', ' – ', ' — ']:
        if sep in target_str:
            parts = target_str.split(sep)
            if len(parts) == 2:
                part1 = _strip_track_number(parts[0].strip())
                part2 = _strip_track_number(parts[1].strip())
                artist = clean_artist or part1
                title = part2 if clean_artist else part2
                return artist, title, raw_album or ""
            elif len(parts) >= 3:
                p_art = _strip_track_number(parts[0].strip())
                p_alb = parts[1].strip()
                p_tit = _strip_track_number(parts[-1].strip())
                return clean_artist or p_art, p_tit, raw_album or p_alb

    artist = clean_artist or ""
    title = clean_title or clean_fn or clean_cap or "Track"
    return artist, title, raw_album or ""


async def fetch_music_metadata(raw_title: str = "", raw_artist: str = "", raw_album: str = "", file_name: str = "", caption: str = "", default_artist: str = "", default_album: str = "") -> Optional[dict]:
    """
    Tự động nhận diện chính xác bài hát & Album từ Apple Music / iTunes API & Deezer API
    Quy tắc an toàn: Tuyệt đối KHÔNG tự ý gán ca sĩ khác nếu file gốc không chứa tên ca sĩ đó.
    """
    artist, title, album_hint = parse_artist_and_title(raw_title, raw_artist or default_artist, raw_album or default_album, file_name, caption)
    
    if not title:
        return None

    # Nếu người dùng có cung cấp ca sĩ mặc định khi quét CD
    if default_artist and (not artist or artist.lower() in ["unknown artist", "unknown"]):
        artist = default_artist

    if default_album and (not album_hint or album_hint.lower() in ["telegram music collection"]):
        album_hint = default_album

    search_query = f"{artist} {title}".strip() if artist else title
    cache_key = search_query.lower()
    if cache_key in _METADATA_CACHE:
        return _METADATA_CACHE[cache_key]

    LOGGER.info(f"[MUSIC SCRAPER] Đang tìm metadata cho: '{search_query}' (Gốc: '{file_name or raw_title}')...")

    # 1. Tìm kiếm trên Apple Music / iTunes API
    candidates: List[dict] = []
    queries_to_try = [search_query]
    if artist and title and search_query != title:
        queries_to_try.append(title)

    for q in queries_to_try:
        try:
            url = f"https://itunes.apple.com/search?term={urllib.parse.quote(q)}&entity=song&limit=5"
            async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("results", []):
                        cand_title = item.get("trackName", "")
                        cand_artist = item.get("artistName", "")
                        cand_album = item.get("collectionName", "")
                        
                        # Tính độ khớp tìm kiếm tổng thể
                        score_full = token_similarity(search_query, f"{cand_artist} {cand_title}")
                        score_title = token_similarity(title, cand_title)
                        
                        # Kiểm tra cả 2 chiều: (Ca sĩ - Bài hát) hoặc (Bài hát - Ca sĩ)
                        match_fwd = (token_similarity(artist, cand_artist) * 0.5 + token_similarity(title, cand_title) * 0.5) if (artist and title) else 0.0
                        match_rev = (token_similarity(artist, cand_title) * 0.5 + token_similarity(title, cand_artist) * 0.5) if (artist and title) else 0.0
                        
                        final_score = max(score_full, score_title * 0.8, match_fwd, match_rev)

                        full_raw_text = (file_name + ' ' + caption + ' ' + raw_title + ' ' + raw_artist).lower()
                        
                        # Nếu cả tên bài hát và tên ca sĩ từ Apple Music đều xuất hiện trong tên file
                        if cand_title.lower() in full_raw_text and cand_artist.lower() in full_raw_text:
                            final_score = max(final_score, 0.95)
                        elif cand_artist.lower() in full_raw_text:
                            final_score = max(final_score, 0.85)
                        elif not artist:
                            # Không có ca sĩ trong file gốc -> Chỉ chấp nhận nếu cand_artist xuất hiện trong filename/caption
                            if cand_artist.lower() not in full_raw_text:
                                continue  # Bỏ qua ứng viên này vì khác ca sĩ
                        else:
                            # Nếu có ca sĩ -> Kiểm tra ca sĩ có khớp không (theo chiều thuận hoặc chiều đảo)
                            artist_score_fwd = token_similarity(artist, cand_artist)
                            artist_score_rev = token_similarity(title, cand_artist)
                            if max(artist_score_fwd, artist_score_rev) < 0.35 and cand_artist.lower() not in full_raw_text:
                                continue  # Ca sĩ không khớp -> Bỏ qua

                            final_score = min(1.0, final_score + 0.25)

                        raw_art = item.get("artworkUrl100", "")
                        hd_cover = raw_art.replace("100x100bb.jpg", "1200x1200bb.webp").replace("100x100bb.png", "1200x1200bb.webp")
                        release_date = item.get("releaseDate", "")
                        year = release_date[:4] if len(release_date) >= 4 else "2026"

                        candidates.append({
                            "score": final_score,
                            "title": cand_title,
                            "artist": cand_artist,
                            "album": cand_album or f"{cand_title} - Single",
                            "cover_url": hd_cover or raw_art,
                            "year": year,
                            "genre": item.get("primaryGenreName", "Pop / Hi-Res"),
                            "publisher": f"{cand_artist} / Apple Music",
                            "source": "Apple Music / iTunes"
                        })
            if candidates:
                break
        except Exception as e:
            LOGGER.warning(f"[MUSIC SCRAPER] iTunes search failed for '{q}': {e}")

    # 2. Nếu tìm thấy candidate hợp lệ (Điểm >= 0.50)
    if candidates:
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]
        if best["score"] >= 0.50:
            _METADATA_CACHE[cache_key] = best
            LOGGER.info(f"[MUSIC SCRAPER] ✅ Khớp chính xác: {best['artist']} - {best['title']} (Album: {best['album']})")
            return best

    # Fallback an toàn: Giữ nguyên tên bài hát và ca sĩ thực tế của file
    fallback_res = {
        "title": title,
        "artist": artist or "Unknown Artist",
        "album": album_hint or "Telegram Music Collection",
        "cover_url": "",
        "year": "2026",
        "genre": "Hi-Res Audio",
        "publisher": "Telegram Cloud Archive",
        "source": "Telegram Direct"
    }
    _METADATA_CACHE[cache_key] = fallback_res
    return fallback_res
