import io
import asyncio
from shazamio import Shazam
from pyrogram.errors import FloodWait, RPCError
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, multi_clients, client_failures, work_loads, USERBOT_CLIENT_INDEX

import os
import tempfile

_SHAZAM = Shazam()
_client_rr_counter = 0


def _get_candidate_clients(preferred_client=None) -> list:
    """Tạo danh sách các bot client luân phiên xoay vòng (round-robin) để chia đều tải tải audio, tránh FloodWait."""
    global _client_rr_counter
    candidates = []
    if preferred_client:
        candidates.append(preferred_client)

    if multi_clients:
        keys = list(multi_clients.keys())
        if keys:
            _client_rr_counter = (_client_rr_counter + 1) % len(keys)
            rotated_keys = keys[_client_rr_counter:] + keys[:_client_rr_counter]
            # Ưu tiên các client ít lỗi trước
            sorted_keys = sorted(
                rotated_keys,
                key=lambda idx: (client_failures.get(idx, 0), work_loads.get(idx, 0))
            )
            for idx in sorted_keys:
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


def extract_embedded_audio_tags(data: bytes) -> dict:
    """
    Trích xuất thuần Python các thẻ metadata gốc được nhúng trực tiếp trong file âm thanh
    (ID3v2 cho MP3/AAC và Vorbis Comments cho FLAC). Không cần cài thêm thư viện ngoài.
    """
    if not data or len(data) < 32:
        return {}
    res = {}

    # 1. Trích xuất ID3v2 (MP3, WAV, AAC)
    if data[:3] == b'ID3':
        try:
            ver_major = data[3]
            tag_size = ((data[6] & 0x7F) << 21) | ((data[7] & 0x7F) << 14) | ((data[8] & 0x7F) << 7) | (data[9] & 0x7F)
            pos = 10
            max_pos = min(len(data), 10 + tag_size)
            frame_map = {
                b'TIT2': 'title',
                b'TPE1': 'artist',
                b'TALB': 'album',
                b'TCON': 'genre',
                b'TYER': 'year',
                b'TDRC': 'year',
            }
            while pos + 10 < max_pos:
                frame_id = data[pos:pos+4]
                if frame_id == b'\x00\x00\x00\x00' or frame_id[:1] == b'\x00':
                    break
                if ver_major == 4:
                    frame_size = ((data[pos+4] & 0x7F) << 21) | ((data[pos+5] & 0x7F) << 14) | ((data[pos+6] & 0x7F) << 7) | (data[pos+7] & 0x7F)
                else:
                    frame_size = int.from_bytes(data[pos+4:pos+8], byteorder='big')
                pos += 10
                if frame_size <= 0 or pos + frame_size > max_pos:
                    break
                if frame_id in frame_map:
                    raw_val = data[pos:pos+frame_size]
                    if len(raw_val) > 1:
                        enc = raw_val[0]
                        payload = raw_val[1:]
                        val_str = ""
                        try:
                            if enc == 0:
                                val_str = payload.decode('iso-8859-1', errors='ignore').strip('\x00').strip()
                            elif enc == 1:
                                val_str = payload.decode('utf-16', errors='ignore').strip('\x00').strip()
                            elif enc == 2:
                                val_str = payload.decode('utf-16-be', errors='ignore').strip('\x00').strip()
                            elif enc == 3:
                                val_str = payload.decode('utf-8', errors='ignore').strip('\x00').strip()
                            else:
                                val_str = payload.decode('utf-8', errors='ignore').strip('\x00').strip()
                        except Exception:
                            pass
                        if val_str and frame_map[frame_id] not in res:
                            res[frame_map[frame_id]] = val_str
                pos += frame_size
        except Exception as e:
            LOGGER.debug(f"[ID3 PARSER] Lỗi phân tích ID3v2: {e}")

    # 2. Trích xuất FLAC Vorbis Comments
    if data[:4] == b'fLaC':
        try:
            pos = 4
            while pos + 4 < len(data):
                header = data[pos:pos+4]
                is_last = bool(header[0] & 0x80)
                block_type = header[0] & 0x7F
                block_len = int.from_bytes(header[1:4], byteorder='big')
                pos += 4
                if block_type == 4:  # VORBIS_COMMENT
                    bdata = data[pos:pos+block_len]
                    bpos = 0
                    if len(bdata) > 4:
                        vendor_len = int.from_bytes(bdata[bpos:bpos+4], byteorder='little')
                        bpos += 4 + vendor_len
                        if bpos + 4 <= len(bdata):
                            comment_count = int.from_bytes(bdata[bpos:bpos+4], byteorder='little')
                            bpos += 4
                            for _ in range(min(comment_count, 100)):
                                if bpos + 4 > len(bdata):
                                    break
                                comm_len = int.from_bytes(bdata[bpos:bpos+4], byteorder='little')
                                bpos += 4
                                if bpos + comm_len > len(bdata):
                                    break
                                comm_str = bdata[bpos:bpos+comm_len].decode('utf-8', errors='ignore')
                                bpos += comm_len
                                if '=' in comm_str:
                                    k, v = comm_str.split('=', 1)
                                    k_low = k.strip().lower()
                                    v = v.strip()
                                    if k_low == 'title' and 'title' not in res:
                                        res['title'] = v
                                    elif k_low in ('artist', 'performer') and 'artist' not in res:
                                        res['artist'] = v
                                    elif k_low == 'album' and 'album' not in res:
                                        res['album'] = v
                                    elif k_low == 'genre' and 'genre' not in res:
                                        res['genre'] = v
                                    elif k_low in ('date', 'year') and 'year' not in res:
                                        res['year'] = v[:4]
                    break
                if is_last or pos + block_len > len(data):
                    break
                pos += block_len
        except Exception as e:
            LOGGER.debug(f"[FLAC PARSER] Lỗi phân tích FLAC Vorbis: {e}")

    return res


async def _query_shazam_file(file_path: str, segment_name: str = "Đoạn 1") -> dict:
    """Gửi tệp âm thanh thực tế tới máy chủ Shazam để trích xuất dấu vân tay âm thanh chuẩn xác."""
    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) < 1024:
        return None
    try:
        if hasattr(_SHAZAM, "recognize"):
            out = await _SHAZAM.recognize(file_path)
        else:
            out = await _SHAZAM.recognize_song(file_path)
        track = out.get("track", {})
        if not track:
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

        LOGGER.info(f"[SHAZAM] Khớp thành công tại [{segment_name}]: {artist} - {title} (Genre: {genre})")

        return {
            "title": title,
            "artist": artist,
            "album": album or f"{title} - Single",
            "cover_url": cover,
            "genre": genre,
            "layer": f"Shazam ({segment_name})",
            "source": "Shazam Fingerprint"
        }
    except Exception as e:
        LOGGER.warning(f"[SHAZAM] Lỗi nhận diện tại [{segment_name}]: {e}")
        return None


async def recognize_audio_from_telegram(
    client=None,
    message=None,
    is_manual: bool = False,
    chat_id: int = None,
    msg_id: int = None,
    log_callback=None,
) -> dict:
    """
    Nhận diện âm thanh đa phân đoạn (Multi-Segment Audio Fingerprinting):
    - Lớp 1A: Shazam mẫu đoạn đầu bài (0s - 20s chuẩn WAV)
    - Lớp 1B: Shazam mẫu đoạn điệp khúc chính (Chorus 35% - 50% thời lượng chuẩn WAV)
    - Lớp 2: Trích xuất trực tiếp thẻ metadata nhúng (ID3v2 / Vorbis Tags) từ file gốc
    Tự động đọc từ Local Cache hoặc xoay vòng Bot Pool Telegram để tải audio mượt mà.
    """
    target_chat_id = chat_id or getattr(getattr(message, "chat", None), "id", None)
    target_msg_id = msg_id or getattr(message, "id", None)

    half_bytes_data = None
    file_name = "Unknown"
    detected_file_size = 0

    # 1. Kiểm tra xem file đã được lưu trong local cache của server chưa
    if target_chat_id and target_msg_id:
        try:
            from Backend.config import Telegram
            cache_dir = getattr(Telegram, "MUSIC_DIR", None) or os.path.join(os.getcwd(), "Music", "cache")
            if not os.path.isabs(cache_dir):
                cache_dir = os.path.join(os.getcwd(), cache_dir)
            if not cache_dir.endswith("cache"):
                cache_dir = os.path.join(cache_dir, "cache")

            for k in [f"{abs(target_chat_id)}_{target_msg_id}.dat", f"{target_chat_id}_{target_msg_id}.dat"]:
                p = os.path.join(cache_dir, k)
                if os.path.exists(p) and os.path.getsize(p) > 1024:
                    detected_file_size = os.path.getsize(p)
                    # Đọc dữ liệu (15MB - 35MB) để có đủ 60s - 90s bài hát
                    if detected_file_size <= 16 * 1024 * 1024:
                        read_limit = max(int(detected_file_size * 0.50), min(detected_file_size, 10 * 1024 * 1024))
                    else:
                        read_limit = min(int(detected_file_size * 0.50), 35 * 1024 * 1024)

                    with open(p, "rb") as cf:
                        half_bytes_data = cf.read(read_limit)

                    if half_bytes_data:
                        LOGGER.info(f"[SHAZAM] Đọc thành công nửa bài ({round(len(half_bytes_data)/1024/1024, 1)}MB) từ Cache cục bộ cho #{target_msg_id}.")
                    break
        except Exception as e:
            LOGGER.warning(f"[SHAZAM] Lỗi kiểm tra cache: {e}")

    # 2. Nếu chưa có cache, tải qua Telegram với cơ chế Round-Robin bot pool
    if not half_bytes_data:
        candidates = _get_candidate_clients(client)
        if not candidates:
            LOGGER.error("[SHAZAM] Không có client Telegram nào khả dụng để tải audio.")
            return None

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
                detected_file_size = getattr(media, "file_size", 0) or 0

                # Tính dung lượng tải (đủ để chứa cả Intro lẫn Điệp khúc)
                if detected_file_size > 0:
                    if detected_file_size <= 16 * 1024 * 1024:
                        half_limit = max(int(detected_file_size * 0.50), min(detected_file_size, 10 * 1024 * 1024))
                    else:
                        half_limit = min(int(detected_file_size * 0.50), 35 * 1024 * 1024)
                else:
                    half_limit = 15 * 1024 * 1024

                limit_mb_str = f"{round(half_limit/1024/1024, 1)}MB"
                LOGGER.info(f"[SHAZAM] Đang tải mẫu bài hát '{file_name}' ({limit_mb_str}) bằng client [{cl_name}]...")
                if log_callback:
                    log_callback(f"Đang tải mẫu âm thanh ({limit_mb_str})...", "info")

                buf = io.BytesIO()
                downloaded = 0
                async for chunk in current_cl.stream_media(target_msg, limit=0):
                    buf.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= half_limit:
                        break

                if buf.tell() > 0:
                    buf.seek(0)
                    half_bytes_data = buf.read()
                break  # Tải thành công
            except FloodWait as fw:
                LOGGER.warning(f"[SHAZAM] Client [{cl_name}] gặp FloodWait ({fw.value}s). Đang đổi bot khác trong pool...")
                _record_client_failure(current_cl, penalty=10)
                await asyncio.sleep(0.3)
                continue
            except Exception as e:
                err_str = str(e)
                if "FLOOD_WAIT" in err_str or "ExportAuthorization" in err_str:
                    LOGGER.warning(f"[SHAZAM] Client [{cl_name}] bị FloodWait/Auth ({e}). Đang đổi bot...")
                    _record_client_failure(current_cl, penalty=10)
                else:
                    LOGGER.warning(f"[SHAZAM] Client [{cl_name}] tải thất bại: {e}. Thử bot khác...")
                    _record_client_failure(current_cl, penalty=2)
                await asyncio.sleep(0.3)
                continue

    if not half_bytes_data:
        LOGGER.error(f"[SHAZAM] Tất cả client đều thất bại khi tải: {file_name}")
        return None

    # ── XỬ LÝ ÂM THANH QUA FILE TẠM & PYDUB (Chuẩn hóa WAV như mic thu âm iPhone) ──
    ext = os.path.splitext(file_name)[1].lower() if file_name else ""
    if ext not in [".mp3", ".flac", ".m4a", ".wav", ".aac", ".ogg"]:
        if half_bytes_data.startswith(b"fLaC"):
            ext = ".flac"
        elif half_bytes_data.startswith(b"RIFF"):
            ext = ".wav"
        elif b"ftyp" in half_bytes_data[:32]:
            ext = ".m4a"
        else:
            ext = ".mp3"

    main_temp_path = None
    sample1_path = None
    sample2_path = None

    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
            tf.write(half_bytes_data)
            main_temp_path = tf.name

        # Dùng pydub giải mã và cắt các phân đoạn âm thanh chuẩn WAV 18s
        audio_seg = None
        total_ms = 0
        try:
            from pydub import AudioSegment
            audio_seg = AudioSegment.from_file(main_temp_path)
            total_ms = len(audio_seg)
        except Exception as pe:
            LOGGER.warning(f"[SHAZAM] Không thể mở qua pydub: {pe}. Sẽ thử trực tiếp file gốc.")

        # ── LỚP 1A: Shazam Phân Đoạn Đầu (0s - 20s chuẩn WAV) ──
        if audio_seg and total_ms > 5000:
            sample1_path = main_temp_path + "_seg1.wav"
            dur1 = min(20000, total_ms)
            audio_seg[:dur1].export(sample1_path, format="wav")
            target_query_path = sample1_path
        else:
            target_query_path = main_temp_path

        if log_callback:
            log_callback("Lớp 1A: Quét dấu vân tay Shazam phân đoạn 1 (0s - 20s)...", "info")
        res1 = await _query_shazam_file(target_query_path, segment_name="Đoạn 1")
        if res1:
            return res1

        # ── LỚP 1B: Shazam Phân Đoạn Điệp Khúc (Chorus ~35% - 50% thời lượng chuẩn WAV) ──
        if audio_seg and total_ms > 25000:
            chorus_start = int(total_ms * 0.40)
            chorus_end = min(chorus_start + 20000, total_ms)
            sample2_path = main_temp_path + "_chorus.wav"
            audio_seg[chorus_start:chorus_end].export(sample2_path, format="wav")

            if log_callback:
                log_callback(f"Đoạn đầu chưa khớp -> Lớp 1B: Quét tập trung Điệp khúc ({int(chorus_start/1000)}s - {int(chorus_end/1000)}s)...", "info")
            LOGGER.info(f"[SHAZAM] Thử quét phân đoạn Điệp khúc ({int(chorus_start/1000)}s - {int(chorus_end/1000)}s) cho: {file_name}")
            res2 = await _query_shazam_file(sample2_path, segment_name="Điệp khúc")
            if res2:
                return res2

        # ── LỚP 1C: Dự phòng quét tệp gốc ──
        if target_query_path != main_temp_path:
            res_full = await _query_shazam_file(main_temp_path, segment_name="Toàn Đoạn")
            if res_full:
                return res_full

        # ── LỚP 2: Trích xuất Thẻ Metadata Gốc (ID3v2 / FLAC Vorbis Comments) từ tệp ──
        if log_callback:
            log_callback("Shazam chưa khớp -> Lớp 2: Đang đọc Thẻ Tag ID3 gốc nhúng trong tệp...", "info")
        embedded_tags = extract_embedded_audio_tags(half_bytes_data)
        if embedded_tags.get("title") and (embedded_tags.get("artist") or embedded_tags.get("album")):
            t_tit = embedded_tags["title"].strip()
            t_art = embedded_tags.get("artist", "").strip()
            t_alb = embedded_tags.get("album", "").strip()
            t_gen = embedded_tags.get("genre", "").strip()

            # Kiểm tra tính hợp lệ của tag (không phải tag rác quảng cáo)
            if len(t_tit) >= 2 and not any(k in t_tit.lower() for k in ["http", "t.me", "@"]):
                LOGGER.info(f"[EMBEDDED TAGS] Trích xuất thành công tag gốc: {t_art} - {t_tit}")
                return {
                    "title": t_tit,
                    "artist": t_art or "Unknown Artist",
                    "album": t_alb or f"{t_tit} - Single",
                    "cover_url": "",
                    "genre": t_gen,
                    "layer": "Thẻ ID3 Tệp Gốc",
                    "source": "Embedded File Tags"
                }

        LOGGER.info(f"[SHAZAM] Không nhận diện được qua Audio Fingerprint & Thẻ gốc cho: {file_name}")
        return None

    finally:
        # Luôn dọn dẹp các tệp âm thanh tạm để giải phóng ổ cứng
        for tp in [main_temp_path, sample1_path, sample2_path]:
            if tp and os.path.exists(tp):
                try:
                    os.remove(tp)
                except Exception:
                    pass


