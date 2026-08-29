import io
import asyncio
from shazamio import Shazam
from pyrogram.errors import FloodWait, RPCError
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, multi_clients, client_failures, work_loads, USERBOT_CLIENT_INDEX

_SHAZAM = Shazam()


def _get_candidate_clients(preferred_client=None) -> list:
    """Tạo danh sách các bot client ưu tiên để tải media, sắp xếp theo tải và điểm lỗi."""
    candidates = []
    if preferred_client:
        candidates.append(preferred_client)

    if multi_clients:
        sorted_indices = sorted(
            multi_clients.keys(),
            key=lambda idx: work_loads.get(idx, 0) + 3 * client_failures.get(idx, 0)
        )
        for idx in sorted_indices:
            cl = multi_clients.get(idx)
            if cl and cl not in candidates:
                candidates.append(cl)

    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
        if botmod.Userbot not in candidates:
            candidates.append(botmod.Userbot)

    if StreamBot and StreamBot not in candidates:
        candidates.append(StreamBot)

    return candidates


def _record_client_failure(client, penalty: int = 1):
    """Ghi nhận lỗi để thuật toán tự động giảm ưu tiên bot này."""
    for idx, cl in multi_clients.items():
        if cl == client:
            client_failures[idx] = client_failures.get(idx, 0) + penalty
            return


async def recognize_audio_from_telegram(
    client=None,
    message=None,
    is_manual: bool = False,
    chat_id: int = None,
    msg_id: int = None,
) -> dict:
    """
    Tải trước đoạn đầu của bài hát và nhận diện qua Shazam.
    Tự động thử lại với các bot khác trong pool nếu gặp FloodWait (ExportAuthorization) hoặc lỗi tải.
    Trả về dict: {"title": ..., "artist": ..., "album": ..., "cover_url": ..., "genre": ...} hoặc None.
    """
    candidates = _get_candidate_clients(client)
    if not candidates:
        LOGGER.error("[SHAZAM] Không có client Telegram nào khả dụng để tải audio.")
        return None

    limit_mb = 10 if is_manual else 2
    limit = 1024 * 1024 * limit_mb

    target_chat_id = chat_id or getattr(getattr(message, "chat", None), "id", None)
    target_msg_id = msg_id or getattr(message, "id", None)

    file_bytes_data = None
    file_name = "Unknown"

    for current_cl in candidates:
        cl_name = getattr(current_cl, "name", "bot")
        try:
            target_msg = message
            if target_chat_id and target_msg_id:
                try:
                    target_msg = await current_cl.get_messages(target_chat_id, target_msg_id)
                except Exception:
                    target_msg = message

            if not target_msg:
                continue

            media = getattr(target_msg, "audio", None) or getattr(target_msg, "document", None)
            if not media:
                continue

            file_name = getattr(media, "file_name", "Unknown")
            LOGGER.info(f"[SHAZAM] Đang tải {limit_mb}MB bài '{file_name}' bằng client [{cl_name}]...")

            buf = io.BytesIO()
            downloaded = 0
            async for chunk in current_cl.stream_media(target_msg, limit=0):
                buf.write(chunk)
                downloaded += len(chunk)
                if downloaded >= limit:
                    break

            if downloaded > 0:
                buf.seek(0)
                file_bytes_data = buf.read()
                break  # Tải thành công
        except FloodWait as fw:
            LOGGER.warning(
                f"[SHAZAM] Client [{cl_name}] gặp FloodWait ({fw.value}s). Đang tự động đổi sang bot khác trong pool..."
            )
            _record_client_failure(current_cl, penalty=10)
            await asyncio.sleep(0.5)
            continue
        except Exception as e:
            err_str = str(e)
            if "FLOOD_WAIT" in err_str or "ExportAuthorization" in err_str:
                LOGGER.warning(
                    f"[SHAZAM] Client [{cl_name}] bị dính FloodWait / ExportAuthorization ({e}). Đang đổi bot khác..."
                )
                _record_client_failure(current_cl, penalty=10)
            else:
                LOGGER.warning(f"[SHAZAM] Client [{cl_name}] tải thất bại: {e}. Thử bot khác...")
                _record_client_failure(current_cl, penalty=2)
            await asyncio.sleep(0.5)
            continue

    if not file_bytes_data:
        LOGGER.error(f"[SHAZAM] Tất cả client đều thất bại khi tải: {file_name}")
        return None

    try:
        out = await _SHAZAM.recognize_song(file_bytes_data)
        track = out.get("track", {})
        if not track:
            LOGGER.info(f"[SHAZAM] Không nhận diện được bài hát cho: {file_name}")
            return None

        title = track.get("title")
        artist = track.get("subtitle")

        sections = track.get("sections", [])
        album = None
        for section in sections:
            if section.get("type") == "SONG":
                for meta in section.get("metadata", []):
                    if meta.get("title") == "Album":
                        album = meta.get("text")
                        break

        cover = track.get("images", {}).get("coverarthq", track.get("images", {}).get("coverart", ""))
        genre = track.get("genres", {}).get("primary")

        LOGGER.info(f"[SHAZAM] Nhận diện thành công: {artist} - {title} (Genre: {genre})")

        return {
            "title": title,
            "artist": artist,
            "album": album or f"{title} - Single",
            "cover_url": cover,
            "genre": genre,
        }
    except Exception as e:
        LOGGER.error(f"[SHAZAM] Lỗi khi gửi dữ liệu sang Shazam: {e}")
        return None

