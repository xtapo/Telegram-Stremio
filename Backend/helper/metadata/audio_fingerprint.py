import io
import asyncio
from typing import Optional, Dict, Tuple, List
from shazamio import Shazam
from pyrogram.errors import FloodWait, RPCError
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, multi_clients, client_failures, work_loads, USERBOT_CLIENT_INDEX

import os
import subprocess
import json
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


def _extract_normalized_segment(
    input_audio_path: str,
    output_wav_path: str,
    start_sec: float,
    duration_sec: float,
    audio_seg_pydub=None
) -> bool:
    """
    Trích xuất và chuẩn hóa phân đoạn âm thanh thành WAV 16-bit 16000Hz Mono
    (Chuẩn tuyệt đối cho Landmark Fingerprint của Shazam & SignatureGenerator).
    """
    # 1. Thử qua FFmpeg CLI trước (nhanh nhất, chuẩn xác nhất, không tốn RAM)
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(max(0.0, round(start_sec, 2))),
            "-t", str(round(duration_sec, 2)),
            "-i", input_audio_path,
            "-ac", "1",           # Downmix về Mono (1 channel)
            "-ar", "16000",       # Resample về 16kHz chuẩn Shazam
            "-c:a", "pcm_s16le",  # PCM 16-bit Little-Endian
            output_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        if res.returncode == 0 and os.path.exists(output_wav_path) and os.path.getsize(output_wav_path) > 4096:
            return True
    except Exception as e:
        LOGGER.debug(f"[SHAZAM EXTRACT] ffmpeg extract failed: {e}")

    # 2. Fallback qua pydub AudioSegment
    if audio_seg_pydub is not None:
        try:
            start_ms = int(max(0.0, start_sec) * 1000)
            end_ms = int((max(0.0, start_sec) + duration_sec) * 1000)
            sub = audio_seg_pydub[start_ms:end_ms]
            # Bắt buộc chuyển sang Mono 16-bit 16000Hz
            sub = sub.set_channels(1).set_frame_rate(16000).set_sample_width(2)
            sub.export(output_wav_path, format="wav")
            if os.path.exists(output_wav_path) and os.path.getsize(output_wav_path) > 4096:
                return True
        except Exception as e:
            LOGGER.debug(f"[SHAZAM EXTRACT] pydub extract failed: {e}")

    return False


def _read_embedded_metadata_file(file_path: str) -> dict:
    """Đọc thẻ metadata gốc (ID3v2, RIFF INFO, Vorbis) trực tiếp từ file âm thanh trên đĩa."""
    if not file_path or not os.path.exists(file_path):
        return {}
    tags = {}
    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=6)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            fmt_tags = data.get("format", {}).get("tags", {})
            low_tags = {k.lower(): v for k, v in fmt_tags.items()}

            title = low_tags.get("title") or low_tags.get("track_title") or low_tags.get("tit2")
            artist = low_tags.get("artist") or low_tags.get("performer") or low_tags.get("tpe1") or low_tags.get("album_artist")
            album = low_tags.get("album") or low_tags.get("talb")
            genre = low_tags.get("genre") or low_tags.get("tcon")
            track_no = low_tags.get("track") or low_tags.get("trck")
            date = low_tags.get("date") or low_tags.get("year") or low_tags.get("tdor") or low_tags.get("tyer")

            if title: tags["title"] = str(title).strip()
            if artist: tags["artist"] = str(artist).strip()
            if album: tags["album"] = str(album).strip()
            if genre: tags["genre"] = str(genre).strip()
            if track_no: tags["track"] = str(track_no).strip()
            if date: tags["year"] = str(date).strip()[:4]
    except Exception as e:
        LOGGER.debug(f"[LOCAL TAGS] ffprobe error on {file_path}: {e}")

    # Fallback pure-python extract_embedded_audio_tags
    if not tags.get("title") or not tags.get("artist"):
        try:
            with open(file_path, "rb") as f:
                header_bytes = f.read(131072)
            emb = extract_embedded_audio_tags(header_bytes)
            if emb.get("title") and "title" not in tags: tags["title"] = emb["title"]
            if emb.get("artist") and "artist" not in tags: tags["artist"] = emb["artist"]
            if emb.get("album") and "album" not in tags: tags["album"] = emb["album"]
            if emb.get("genre") and "genre" not in tags: tags["genre"] = emb["genre"]
        except Exception:
            pass

    return tags


async def _query_shazam_file(file_path: str, segment_name: str = "Đoạn 1", log_callback=None) -> dict:
    """Gửi tệp âm thanh thực tế tới máy chủ Shazam để trích xuất dấu vân tay âm thanh chuẩn xác."""
    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) < 1024:
        return None

    # Thử với endpoint VN trước (phù hợp kho nhạc Việt Nam), nếu không khớp thì fallback sang US
    endpoint_configs = [
        ("vi-VN", "VN"),
        ("en-US", "US"),
    ]

    for lang, country in endpoint_configs:
        try:
            shz = Shazam(language=lang, endpoint_country=country)
            out = None
            if hasattr(shz, "recognize"):
                try:
                    out = await shz.recognize(file_path)
                except Exception as ex_rec:
                    LOGGER.debug(f"[SHAZAM] shz.recognize failed ({ex_rec}), trying fallback...")

            if (not out or not out.get("track")) and hasattr(shz, "recognize_song"):
                try:
                    out = await shz.recognize_song(file_path)
                except Exception:
                    pass

            if not out:
                continue

            track = out.get("track", {})
            if not track:
                continue

            title = track.get("title")
            artist = track.get("subtitle")
            if not title or not artist:
                continue

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

            LOGGER.info(f"[SHAZAM] Khớp thành công tại [{segment_name}] ({country}): {artist} - {title} (Genre: {genre})")

            return {
                "title": title,
                "artist": artist,
                "album": album or f"{title} - Single",
                "cover_url": cover,
                "genre": genre,
                "layer": f"Shazam [{segment_name}]",
                "source": "Shazam Fingerprint"
            }
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}"
            LOGGER.warning(f"[SHAZAM] Lỗi nhận diện tại [{segment_name}] ({country}): {err_msg}")
            if country == endpoint_configs[-1][1] and log_callback:
                log_callback(f"Lỗi kết nối Shazam [{segment_name}]: {err_msg}", "warn")
            continue

    return None


async def recognize_audio_from_telegram(
    client=None,
    message=None,
    is_manual: bool = False,
    chat_id: int = None,
    msg_id: int = None,
    log_callback=None,
    local_file_path: str = None,
) -> dict:
    """
    Nhận diện âm thanh đa phân đoạn (Multi-Segment Audio Fingerprinting):
    - Lớp 1: Shazam qua các phân đoạn âm thanh vàng chuẩn hóa Mono 16kHz 16-bit (Điệp khúc, Verse, Pre-Chorus)
    - Lớp 2: Trích xuất trực tiếp thẻ metadata gốc nhúng (ID3v2, RIFF INFO, Vorbis) qua ffprobe và parser nhúng
    Tự động tận dụng tối đa Local File, Local Cache hoặc xoay vòng Bot Pool Telegram để tải mẫu audio đầy đủ.
    """
    target_chat_id = chat_id or getattr(getattr(message, "chat", None), "id", None)
    target_msg_id = msg_id or getattr(message, "id", None)

    source_audio_path = None
    created_temp_file = None
    file_name = "Unknown"
    detected_file_size = 0

    # 0. Nếu truyền trực tiếp đường dẫn file cục bộ (Local File)
    if local_file_path and os.path.exists(local_file_path) and os.path.getsize(local_file_path) > 1024:
        source_audio_path = local_file_path
        detected_file_size = os.path.getsize(local_file_path)
        file_name = os.path.basename(local_file_path)
        size_mb_str = f"{round(detected_file_size/1024/1024, 1)}MB"
        LOGGER.info(f"[SHAZAM] Sử dụng tệp âm thanh cục bộ: {local_file_path} ({size_mb_str})")
        if log_callback:
            log_callback(f"Nhận diện tệp âm thanh cục bộ: {file_name} ({size_mb_str})...", "info")

    # 1. Kiểm tra cache cục bộ (Nếu máy chủ đã lưu sẵn file .dat hoàn chỉnh)
    if not source_audio_path and target_chat_id and target_msg_id:
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
                    source_audio_path = p
                    detected_file_size = os.path.getsize(p)
                    size_mb_str = f"{round(detected_file_size/1024/1024, 1)}MB"
                    LOGGER.info(f"[SHAZAM] Sử dụng tệp từ Cache cục bộ: {p} ({size_mb_str})")
                    if log_callback:
                        log_callback(f"Sử dụng tệp từ bộ nhớ đệm máy chủ ({size_mb_str})...", "info")
                    break
        except Exception as e:
            LOGGER.warning(f"[SHAZAM] Lỗi kiểm tra cache: {e}")

    # 2. Nếu chưa có cache, tải qua Telegram với cơ chế Round-Robin bot pool
    if not source_audio_path:
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

                # Tải mẫu từ 25MB - 35MB (đủ trích xuất cả Intro, Verse lẫn Điệp khúc)
                if detected_file_size > 0:
                    download_limit = min(detected_file_size, max(25 * 1024 * 1024, int(detected_file_size * 0.60)))
                else:
                    download_limit = 25 * 1024 * 1024

                limit_mb_str = f"{round(download_limit/1024/1024, 1)}MB"
                LOGGER.info(f"[SHAZAM] Đang tải mẫu bài hát '{file_name}' ({limit_mb_str}) bằng client [{cl_name}]...")
                if log_callback:
                    log_callback(f"Đang tải mẫu âm thanh ({limit_mb_str})...", "info")

                ext = os.path.splitext(file_name)[1].lower() if file_name else ""
                if ext not in [".mp3", ".flac", ".m4a", ".wav", ".aac", ".ogg"]:
                    ext = ".audio"

                tf = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                created_temp_file = tf.name

                downloaded = 0
                async for chunk in current_cl.stream_media(target_msg, limit=0):
                    tf.write(chunk)
                    downloaded += len(chunk)
                    if downloaded >= download_limit:
                        break

                tf.close()

                if os.path.exists(created_temp_file) and os.path.getsize(created_temp_file) > 1024:
                    source_audio_path = created_temp_file
                    break
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

    if not source_audio_path or not os.path.exists(source_audio_path) or os.path.getsize(source_audio_path) < 1024:
        LOGGER.error(f"[SHAZAM] Không có dữ liệu âm thanh hợp lệ cho: {file_name}")
        return None

    try:
        # Xác định tổng thời lượng âm thanh bằng ffprobe
        total_sec = 0.0
        try:
            cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", source_audio_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                total_sec = float(res.stdout.strip())
        except Exception:
            pass

        audio_seg = None
        if total_sec <= 0:
            try:
                from pydub import AudioSegment
                audio_seg = AudioSegment.from_file(source_audio_path)
                total_sec = len(audio_seg) / 1000.0
            except Exception as pe:
                LOGGER.debug(f"[SHAZAM] Pydub open failed: {pe}")

        LOGGER.info(f"[SHAZAM] Thời lượng tệp mẫu phân tích: {round(total_sec, 1)}s")

        # Định nghĩa các cửa sổ âm thanh vàng (chuẩn 25 giây để nhận diện vân tay rõ nhất)
        scan_windows = []
        if total_sec >= 90:
            # 1. Điệp khúc chính: ~70s - 95s
            c1 = min(70.0, max(0.0, total_sec - 25.0))
            scan_windows.append(("Điệp khúc chính", c1, 25.0))
            # 2. Lời hát mở đầu Verse 1: ~26s - 51s (bỏ qua đoạn dạo đầu không lời)
            scan_windows.append(("Đoạn hát Verse 1", 26.0, 25.0))
            # 3. Điệp khúc 2 / Cao trào (nếu bài dài >= 125s)
            if total_sec >= 125:
                c2 = min(98.0, total_sec - 25.0)
                scan_windows.append(("Điệp khúc 2 / Cao trào", c2, 25.0))
            # 4. Tiền điệp khúc Pre-Chorus: ~48s - 73s
            scan_windows.append(("Tiền Điệp khúc", 48.0, 25.0))
            # 5. Đoạn đầu bài hát: ~6s - 31s
            scan_windows.append(("Đầu bài hát", 6.0, 25.0))
        elif total_sec >= 45:
            scan_windows.append(("Điệp khúc", total_sec * 0.50, min(25.0, total_sec * 0.45)))
            scan_windows.append(("Đoạn hát Verse 1", 15.0, min(25.0, total_sec - 15.0)))
            scan_windows.append(("Đầu bài hát", 3.0, min(25.0, total_sec - 3.0)))
        elif total_sec > 5:
            scan_windows.append(("Toàn bộ bài hát", 0.0, total_sec))
        else:
            scan_windows.append(("Mẫu âm thanh", 0.0, 25.0))

        # Quét lần lượt qua các cửa sổ âm thanh đã chuẩn hóa Mono 16kHz 16-bit PCM WAV
        for seg_idx, (seg_name, start_s, dur_s) in enumerate(scan_windows, start=1):
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            sample_w_path = tmp_wav.name
            tmp_wav.close()
            try:
                ok = _extract_normalized_segment(
                    input_audio_path=source_audio_path,
                    output_wav_path=sample_w_path,
                    start_sec=start_s,
                    duration_sec=dur_s,
                    audio_seg_pydub=audio_seg
                )
                if not ok:
                    continue

                t_from = int(start_s)
                t_to = int(start_s + dur_s)
                if log_callback:
                    if seg_idx == 1:
                        log_callback(f"Lớp 1: Quét vân tay Shazam [{seg_name}] ({t_from}s - {t_to}s)...", "info")
                    else:
                        log_callback(f"Chưa khớp -> Quét tiếp Shazam [{seg_name}] ({t_from}s - {t_to}s)...", "info")
                LOGGER.info(f"[SHAZAM] Quét vân tay tại [{seg_name}] ({t_from}s - {t_to}s) cho: {file_name}")

                res = await _query_shazam_file(sample_w_path, segment_name=seg_name, log_callback=log_callback)
                if res:
                    return res
            finally:
                if os.path.exists(sample_w_path):
                    try:
                        os.remove(sample_w_path)
                    except Exception:
                        pass

        # Thử 1 lần cuối: quét trực tiếp đoạn 30s đầu bài từ nguồn chuẩn hóa
        tmp_final_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        final_sample_path = tmp_final_wav.name
        tmp_final_wav.close()
        try:
            ok = _extract_normalized_segment(
                input_audio_path=source_audio_path,
                output_wav_path=final_sample_path,
                start_sec=0.0,
                duration_sec=min(30.0, total_sec) if total_sec > 0 else 30.0,
                audio_seg_pydub=audio_seg
            )
            if ok:
                if log_callback:
                    log_callback("Quét mở rộng toàn dải âm thanh đầu bài (0s - 30s)...", "info")
                res = await _query_shazam_file(final_sample_path, segment_name="Toàn dải đầu", log_callback=log_callback)
                if res:
                    return res
        finally:
            if os.path.exists(final_sample_path):
                try:
                    os.remove(final_sample_path)
                except Exception:
                    pass

        # ── LỚP 2: Trích xuất Thẻ Metadata Gốc (ID3v2, RIFF INFO, FLAC Vorbis) từ tệp ──
        if log_callback:
            log_callback("Shazam chưa khớp -> Lớp 2: Đang đọc Thẻ Tag ID3 / Metadata gốc nhúng trong tệp...", "info")

        embedded_tags = _read_embedded_metadata_file(source_audio_path)
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
        if created_temp_file and os.path.exists(created_temp_file):
            try:
                os.remove(created_temp_file)
            except Exception:
                pass


async def recognize_audio_from_local_file(
    file_path: str,
    log_callback=None,
) -> Optional[dict]:
    """
    Nhận diện âm thanh Đa Lớp (Shazam 5 cửa sổ vàng 16kHz Mono + Thẻ Tag ID3/RIFF gốc)
    trực tiếp từ file âm thanh cục bộ trên ổ đĩa. Tốc độ cực nhanh (1-2 giây) không cần qua mạng Telegram.
    """
    if not file_path or not os.path.exists(file_path):
        return None
    return await recognize_audio_from_telegram(
        local_file_path=file_path,
        log_callback=log_callback
    )



