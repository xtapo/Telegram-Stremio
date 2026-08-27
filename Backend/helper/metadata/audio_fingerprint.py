import io
from shazamio import Shazam
from Backend.logger import LOGGER

_SHAZAM = Shazam()

async def recognize_audio_from_telegram(client, message, is_manual: bool = False) -> dict:
    """
    Tải trước đoạn đầu của bài hát và nhận diện qua Shazam.
    Trả về dict: {"title": ..., "artist": ..., "album": ..., "cover_url": ...} hoặc None.
    """
    try:
        media = getattr(message, "audio", None) or getattr(message, "document", None)
        file_name = getattr(media, 'file_name', 'Unknown')
        
        limit_mb = 10 if is_manual else 2
        LOGGER.info(f"[SHAZAM] Đang tải {limit_mb}MB để nhận diện file: {file_name}")
        
        file_bytes = io.BytesIO()
        downloaded = 0
        limit = 1024 * 1024 * limit_mb

        
        async for chunk in client.stream_media(message, limit=0):
            file_bytes.write(chunk)
            downloaded += len(chunk)
            if downloaded >= limit:
                break
                
        file_bytes.seek(0)
        out = await _SHAZAM.recognize_song(file_bytes.read())
        
        track = out.get('track', {})
        if not track:
            LOGGER.info(f"[SHAZAM] Không nhận diện được bài hát cho: {file_name}")
            return None
            
        title = track.get('title')
        artist = track.get('subtitle')
        
        sections = track.get('sections', [])
        album = None
        for section in sections:
            if section.get('type') == 'SONG':
                for meta in section.get('metadata', []):
                    if meta.get('title') == 'Album':
                        album = meta.get('text')
                        break
                        
        cover = track.get('images', {}).get('coverarthq', track.get('images', {}).get('coverart', ''))
        genre = track.get('genres', {}).get('primary')
        
        LOGGER.info(f"[SHAZAM] Nhận diện thành công: {artist} - {title} (Genre: {genre})")
        
        return {
            "title": title,
            "artist": artist,
            "album": album or f"{title} - Single",
            "cover_url": cover,
            "genre": genre
        }
    except Exception as e:
        LOGGER.error(f"[SHAZAM] Lỗi nhận diện: {e}")
        return None
