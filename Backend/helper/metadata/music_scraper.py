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
    fn = re.sub(r'\.(mp3|flac|m4a|wav|aac|ogg|opus|alac|dsf|ape)$', '', fn, flags=re.IGNORECASE)
    
    # 2. Bỏ @channel username (ví dụ: @nhachot_2026, @MyChannel)
    fn = re.sub(r'@[^\s_.-]+[_\s.-]*', ' ', fn)
    
    # 3. Bỏ nội dung trong ngoặc vuông [320kbps], [FLAC 24-96], [Official], [NhacCuaTui]
    fn = re.sub(r'\[.*?\]', ' ', fn)
    
    # 4. Bỏ các tag trong ngoặc tròn như (Official Music Video), (Lyric Video), (Audio), (Remastered)
    fn = re.sub(r'\((Official|Lyric|Audio|Visualizer|Remastered|Album Version|Explicit|Video|Bonus|Deluxe|Live|MV|Full MV).*?\)', ' ', fn, flags=re.IGNORECASE)
    
    # 5. Bỏ các từ khóa chất lượng
    fn = re.sub(r'\b(320kbps|128kbps|256kbps|FLAC|MP3|WAV|24bit|16bit|96kHz|44\.1kHz|Hi-Res|Lossless|Kbps|HQ|HD|4K|1080p)\b', ' ', fn, flags=re.IGNORECASE)
    
    # 6. Chuẩn hóa khoảng trắng, dấu chấm, gạch dưới
    fn = fn.replace('_', ' ')
    fn = re.sub(r'\.+', ' ', fn)
    fn = re.sub(r'\s*-\s*', ' - ', fn)
    
    # 7. Bỏ số thứ tự bài hát ở đầu (ví dụ: "01. ", "01 - ", "01_", "1-02 ", "Track 01 ")
    fn = re.sub(r'^\s*(\d{1,3}[\.\-_\s]+|\bTrack\s*\d+\b\s*[\.\-_\s]*|[A-D]\d+[\.\-_\s]+)', '', fn)
    
    fn = re.sub(r'\s+', ' ', fn).strip()
    return fn


def extract_context_from_text(text: str) -> Tuple[str, str]:
    """
    Trích xuất tên Album và Ca Sĩ từ tin nhắn văn bản, caption hoặc tựa đề gần chỗ gửi file nhạc.
    Hỗ trợ cả tiếng Việt có dấu lẫn không dấu.
    Ví dụ:
      - '💿 Album: Khúc Tình Xưa'       (có dấu)
      - 'Ca si: Le Quyen'                (không dấu)
      - 'Le Quyen - Khuc Tinh Xua [FLAC]' (không dấu, dạng dòng)
    """
    if not text:
        return "", ""
    text = text.strip()
    artist = ""
    album = ""

    # 1. Tìm theo nhãn rõ ràng — hỗ trợ cả có dấu và không dấu
    #    Ca sĩ / Ca si / Nghệ sĩ / Nghe si / Trình bày / Trinh bay / Artist / Singer / Hat / Hát
    artist_labels = (
        r'Ca\s*s[ĩỹi]'        # Ca sĩ / Ca sỹ / Ca si
        r'|Ngh[eệ]\s*s[ĩi]'   # Nghệ sĩ / Nghe si
        r'|Tr[iì]nh\s*b[aà]y' # Trình bày / Trinh bay
        r'|H[aá]t'             # Hát / Hat
        r'|Artist|Singer|Performer'
    )
    m_artist = re.search(
        rf'(?:{artist_labels})\s*[:\-]\s*([^\n\r,;]+)', text, re.IGNORECASE
    )
    if m_artist:
        artist = m_artist.group(1).strip()

    #    Album / CD / Tuyển tập / Tuyen tap / Đĩa hát / Dia hat / Collection / Nhac tuyen
    album_labels = (
        r'Album'
        r'|CD\s*\d*'
        r'|Tuy[eể]n\s*t[aậ]p'  # Tuyển tập / Tuyen tap
        r'|[ĐD][ĩi]a\s*h[aá]t' # Đĩa hát / Dia hat
        r'|Collection'
        r'|Nh[aạ]c\s*tuy[eể]n'  # Nhạc tuyển / Nhac tuyen
    )
    m_album = re.search(
        rf'(?:{album_labels})\s*[:\-]\s*([^\n\r,;]+)', text, re.IGNORECASE
    )
    if m_album:
        album = m_album.group(1).strip()

    # 2. Nếu là dạng dòng đầu 'Artist - Album' hoặc 'Artist - Album (Year)'
    if not artist or not album:
        first_line = text.split('\n')[0].strip()
        # Loại bỏ emoji / icon ở đầu dòng
        first_line = re.sub(r'^[^\w\s\u00C0-\u1EF9]+', '', first_line).strip()
        # Loại bỏ tag [FLAC], [WAV], [320kbps]...
        first_line = re.sub(r'\[.*?\]', '', first_line).strip()
        # Loại bỏ năm trong ngoặc (2010), (2024)
        first_line = re.sub(r'\((?:19|20)\d{2}\)', '', first_line).strip()

        if ' - ' in first_line:
            parts = first_line.split(' - ')
            if len(parts) >= 2:
                if not artist: artist = parts[0].strip()
                if not album: album = parts[1].strip()

    return artist, album


def parse_artist_and_title(raw_title: str = "", raw_artist: str = "", raw_album: str = "", file_name: str = "", caption: str = "") -> Tuple[str, str, str]:
    """
    Trích xuất Artist, Title, Album một cách chính xác nhất từ nhiều nguồn dữ liệu của Telegram
    """
    clean_fn = clean_audio_filename(file_name)
    clean_cap = clean_audio_filename(caption)
    clean_title = clean_audio_filename(raw_title)
    clean_artist = clean_audio_filename(raw_artist)
    
    # Loại bỏ artist nếu chứa tên channel hoặc rác
    if clean_artist and ('@' in clean_artist or clean_artist.lower() in ["unknown artist", "unknown", "va", "various artists", "telegram"]):
        clean_artist = ""

    # Trường hợp 1: ID3 Tag đã có đầy đủ Artist & Title chuẩn
    if clean_artist and clean_title and clean_title.lower() != clean_artist.lower():
        return clean_artist, clean_title, raw_album or ""

    # Trường hợp 2: Phân tách từ filename dạng "Artist - Title" hoặc "Title - Artist"
    target_str = clean_title or clean_fn or clean_cap
    if ' - ' in target_str:
        parts = target_str.split(' - ')
        if len(parts) == 2:
            part1 = parts[0].strip()
            part2 = parts[1].strip()
            # Thường part1 là Artist, part2 là Title
            artist = clean_artist or part1
            title = part2 if clean_artist else part2
            return artist, title, raw_album or ""
        elif len(parts) >= 3:
            # Dạng "Artist - Album - Title" hoặc "Artist - Track - Title"
            return parts[0].strip(), parts[-1].strip(), parts[1].strip()

    # Trường hợp 3: Không có dấu gạch ngang, dùng chuỗi đã làm sạch
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
                        
                        score_full = token_similarity(search_query, f"{cand_artist} {cand_title}")
                        score_title = token_similarity(title, cand_title)
                        
                        final_score = max(score_full, score_title * 0.8)

                        # KIỂM TRA NGHIÊM NGẶT:
                        # Nếu file gốc KHÔNG có ca sĩ (chỉ có tên bài hát như "Chiếc lá cuối cùng"),
                        # thì KHÔNG được tự tiện gán một ca sĩ ngẫu nhiên từ mạng (như Khánh Phương thay vì Lệ Quyên)!
                        if not artist:
                            # Không có ca sĩ trong file gốc -> Chỉ chấp nhận nếu cand_artist xuất hiện trong filename/caption
                            if cand_artist.lower() not in (file_name + ' ' + caption + ' ' + raw_title).lower():
                                continue  # Bỏ qua ứng viên này vì khác ca sĩ
                        else:
                            # Nếu có ca sĩ -> Kiểm tra ca sĩ có khớp không
                            artist_score = token_similarity(artist, cand_artist)
                            if artist_score < 0.4 and artist.lower() not in cand_artist.lower() and cand_artist.lower() not in artist.lower():
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
