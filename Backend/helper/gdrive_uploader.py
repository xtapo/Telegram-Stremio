import asyncio
import os
import re
import shutil
import tempfile
import time
import urllib.parse
import zipfile
import tarfile
from typing import Dict, List, Optional, Tuple

import httpx
from pyrogram.errors import FloodWait

from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot
from Backend.helper.metadata.music_scraper import (
    clean_audio_filename,
    extract_context_from_text,
    fetch_music_metadata,
)

AUDIO_EXTENSIONS = (
    ".mp3", ".flac", ".m4a", ".wav", ".aac", 
    ".alac", ".ogg", ".opus", ".dsf", ".dff", ".ape", ".aiff"
)
ARCHIVE_EXTENSIONS = (".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz", ".bz2", ".xz", ".iso")
IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")

TEMP_UPLOAD_DIR = os.path.abspath(os.path.join("Music", "temp_uploads"))
CACHE_DOWNLOAD_DIR = os.path.abspath(os.path.join("Music", "temp_uploads", "cached_downloads"))
os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)
os.makedirs(CACHE_DOWNLOAD_DIR, exist_ok=True)


def _find_7z_binary() -> Optional[str]:
    """Tìm kiếm file thực thi 7-Zip hoặc WinRAR trên hệ thống"""
    candidates = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        shutil.which("7z"),
        shutil.which("7za"),
        r"C:\Windows\system32\7z.EXE",
        r"C:\Program Files\WinRAR\WinRAR.exe",
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
        shutil.which("rar"),
        shutil.which("unrar"),
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


def _sync_extract_archive(archive_path: str, extract_dir: str) -> Tuple[bool, str]:
    """
    Hàm giải nén đồng bộ (chạy trong worker thread):
    Thử lần lượt tất cả các công cụ 7-Zip, WinRAR, UnRAR, Python zip/7z/tar.
    Trả về (success, error_or_success_message).
    """
    import subprocess
    os.makedirs(extract_dir, exist_ok=True)
    ext = os.path.splitext(archive_path)[1].lower()

    archiver_candidates = []
    for p in [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
        shutil.which("7z"),
        shutil.which("7za"),
        r"C:\Windows\system32\7z.EXE",
        "/usr/bin/7z",
        "/usr/bin/7za",
        "/usr/local/bin/7z",
        shutil.which("unrar"),
        shutil.which("unrar-free"),
        "/usr/bin/unrar",
        "/usr/bin/unrar-free",
        r"C:\Program Files\WinRAR\WinRAR.exe",
        r"C:\Program Files\WinRAR\UnRAR.exe",
        r"C:\Program Files (x86)\WinRAR\UnRAR.exe",
        shutil.which("rar"),
    ]:
        if p and os.path.exists(p) and p not in archiver_candidates:
            archiver_candidates.append(p)

    # Nếu đang chạy trong Linux/Docker mà chưa cài 7z, tự động cài đặt ngầm p7zip-full
    if os.name != "nt" and not archiver_candidates and shutil.which("apt-get"):
        try:
            LOGGER.info("[AUTO INSTALL] Linux archiver not found in Docker. Installing p7zip-full...")
            subprocess.run(["apt-get", "update", "-qq"], timeout=60)
            subprocess.run(["apt-get", "install", "-y", "-qq", "--no-install-recommends", "p7zip-full", "unrar-free"], timeout=120)
            for p in ["/usr/bin/7z", "/usr/bin/7za", "/usr/bin/unrar", "/usr/bin/unrar-free"]:
                if os.path.exists(p) and p not in archiver_candidates:
                    archiver_candidates.append(p)
        except Exception as e:
            LOGGER.warning(f"[AUTO INSTALL ERROR] {e}")

    last_error = ""
    # 1. Thử tất cả các công cụ CLI đã tìm thấy
    for archiver in archiver_candidates:
        try:
            is_winrar = "winrar" in archiver.lower() or "unrar" in archiver.lower()
            if is_winrar:
                cmd = [archiver, "x", "-y", archive_path, extract_dir]
            else:
                cmd = [archiver, "x", "-y", f"-o{extract_dir}", archive_path]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if res.returncode == 0:
                LOGGER.info(f"[EXTRACT SUCCESS] Extracted with {os.path.basename(archiver)}: {archive_path}")
                return True, f"Đã giải nén thành công bằng {os.path.basename(archiver)}"
            else:
                err_text = (res.stderr or res.stdout or "").strip()
                err_lines = [
                    l.strip() for l in err_text.splitlines() 
                    if l.strip() and not l.startswith("7-Zip") 
                    and not l.startswith("Scanning") 
                    and not l.startswith("Path =") 
                    and not l.startswith("Type =") 
                    and not l.startswith("Physical Size")
                    and not l.startswith("Everything is Ok")
                ]
                err_detail = " | ".join(err_lines[:2]) if err_lines else f"Exit code {res.returncode}"
                last_error = f"{os.path.basename(archiver)}: {err_detail}"
                LOGGER.warning(f"[EXTRACT WARN] {archiver} failed ({res.returncode}): {err_text}")
        except Exception as e:
            last_error = f"{os.path.basename(archiver)}: {e}"
            LOGGER.warning(f"[EXTRACT CLI ERROR] {e}")

    # 2. Thử thư viện Python rarfile cho file .rar
    if ext == ".rar":
        try:
            import rarfile
            for archiver in archiver_candidates:
                rarfile.UNRAR_TOOL = archiver
                try:
                    with rarfile.RarFile(archive_path) as rf:
                        rf.extractall(path=extract_dir)
                    return True, f"Đã giải nén thành công bằng rarfile ({os.path.basename(archiver)})"
                except Exception as ex_rf:
                    LOGGER.debug(f"rarfile with {archiver} note: {ex_rf}")
        except Exception as e:
            if not last_error: last_error = f"rarfile: {e}"

    # 3. Python zipfile (.zip)
    if ext == ".zip":
        try:
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(extract_dir)
            return True, "Đã giải nén thành công bằng Python ZipFile"
        except Exception as e:
            if not last_error: last_error = f"ZipFile: {e}"

    # 4. Python py7zr (.7z)
    if ext == ".7z":
        try:
            import py7zr
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=extract_dir)
            return True, "Đã giải nén thành công bằng py7zr"
        except Exception as e:
            if not last_error: last_error = f"py7zr: {e}"

    # 5. Python tarfile (.tar, .tar.gz, .tgz, .bz2, .xz)
    if ext in (".tar", ".tar.gz", ".tgz", ".bz2", ".xz"):
        try:
            with tarfile.open(archive_path, 'r:*') as tf:
                tf.extractall(extract_dir)
            return True, "Đã giải nén thành công bằng Python TarFile"
        except Exception as e:
            if not last_error: last_error = f"TarFile: {e}"

    return False, last_error or f"Không có công cụ nào giải nén được file {ext} này hoặc file bị hỏng / có mật khẩu."


async def _extract_archive(archive_path: str, extract_dir: str) -> Tuple[bool, str]:
    """Chạy giải nén trong threadpool tránh block event loop và tránh lỗi event loop trên Windows"""
    return await asyncio.to_thread(_sync_extract_archive, archive_path, extract_dir)


def parse_gdrive_url(url: str) -> Tuple[str, str]:
    """
    Phân tích URL Google Drive và trả về:
    (link_type, resource_id)
    link_type: 'file' | 'folder' | 'direct' | 'invalid'
    """
    if not url:
        return "invalid", ""

    url = url.strip()

    # 1. Thư mục Google Drive (Folder)
    folder_match = re.search(r'drive\.google\.com/drive/(?:u/\d+/)?folders/([a-zA-Z0-9_-]+)', url)
    if folder_match:
        return "folder", folder_match.group(1)

    folder_param = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if "folders" in url and folder_param:
        return "folder", folder_param.group(1)

    # 2. File đơn lẻ Google Drive
    file_match = re.search(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)', url)
    if file_match:
        return "file", file_match.group(1)

    file_uc = re.search(r'drive\.google\.com/(?:uc|open)\?.*id=([a-zA-Z0-9_-]+)', url)
    if file_uc:
        return "file", file_uc.group(1)

    file_direct_uc = re.search(r'drive\.usercontent\.google\.com/download\?.*id=([a-zA-Z0-9_-]+)', url)
    if file_direct_uc:
        return "file", file_direct_uc.group(1)

    # 3. Chuỗi ID thuần
    if re.match(r'^[a-zA-Z0-9_-]{25,}$', url):
        return "file", url

    # 4. Link tải trực tiếp từ nguồn khác (HTTP/HTTPS)
    if url.startswith("http://") or url.startswith("https://"):
        return "direct", url

    return "invalid", ""


def _extract_filename_from_headers(headers: httpx.Headers, default_name: str = "downloaded_file") -> str:
    cd = headers.get("content-disposition", "")
    if cd:
        # Chuẩn RFC 5987: filename*=UTF-8''...
        fn_star = re.search(r"filename\*\s*=\s*UTF-8''([^;]+)", cd, re.I)
        if fn_star:
            return urllib.parse.unquote(fn_star.group(1).strip('"\' '))
        # Chuẩn thường: filename="..."
        fn_match = re.search(r'filename\s*=\s*"([^"]+)"', cd, re.I) or re.search(r'filename\s*=\s*([^;]+)', cd, re.I)
        if fn_match:
            return fn_match.group(1).strip('"\' ')
    return default_name


async def _get_upload_client():
    """
    Ưu tiên lấy Userbot (User Session) để đạt tốc độ upload tối đa và hỗ trợ file lớn đến 2GB/4GB.
    Nếu chưa kích hoạt, tự động thử kích hoạt từ session đã lưu trong database.
    Fallback về StreamBot nếu không có Userbot.
    """
    # 1. Kiểm tra Userbot đang kết nối
    if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
        return botmod.Userbot, "user_session"

    # 2. Thử kích hoạt Userbot từ DB
    try:
        from Backend.helper.session_auth import get_active_session_string, _activate
        session_str = await get_active_session_string()
        if session_str:
            await _activate(session_str)
            if botmod.Userbot and getattr(botmod.Userbot, "is_connected", False):
                return botmod.Userbot, "user_session"
    except Exception as e:
        LOGGER.warning(f"[GDRIVE UPLOAD] Không thể kích hoạt Userbot: {e}")

    # 3. Fallback StreamBot
    return StreamBot, "bot"


class GoogleDriveUploadManager:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._cancel_requested: bool = False
        self._status: str = "idle"  # idle | downloading | uploading | indexing | completed | cancelled | error
        self._stage: str = ""
        self._current_file: str = ""
        self._file_index: int = 0
        self._total_files: int = 0
        self._download_percent: int = 0
        self._download_bytes: int = 0
        self._download_total: int = 0
        self._upload_percent: int = 0
        self._upload_bytes: int = 0
        self._upload_total: int = 0
        self._speed_str: str = ""
        self._error_message: str = ""
        self._start_time: float = 0.0
        self._end_time: float = 0.0
        self._logs: List[dict] = []
        self._client_type: str = "bot"
        self._uploaded_tracks: List[dict] = []
        self._channel_id: str = ""

    def get_status(self) -> dict:
        elapsed = 0
        if self._start_time > 0:
            end = self._end_time if self._end_time > 0 else time.time()
            elapsed = int(end - self._start_time)

        return {
            "status": self._status,
            "stage": self._stage,
            "current_file": self._current_file,
            "file_index": self._file_index,
            "total_files": self._total_files,
            "download_percent": self._download_percent,
            "download_bytes": self._download_bytes,
            "download_total": self._download_total,
            "upload_percent": self._upload_percent,
            "upload_bytes": self._upload_bytes,
            "upload_total": self._upload_total,
            "speed": self._speed_str,
            "error_message": self._error_message,
            "elapsed_seconds": elapsed,
            "client_type": self._client_type,
            "uploaded_count": len(self._uploaded_tracks),
            "logs": self._logs[-30:],
        }

    def _log(self, msg: str, log_type: str = "info"):
        LOGGER.info(f"[GDRIVE UPLOAD] {msg}")
        self._logs.append({
            "time": time.strftime("%H:%M:%S"),
            "msg": msg,
            "type": log_type
        })
        if len(self._logs) > 100:
            self._logs.pop(0)

    async def start(
        self,
        url: str,
        target_channel_id: str,
        default_artist: str = "",
        default_album: str = "",
        auto_scrape: bool = True,
        send_as_document: bool = False,
    ) -> dict:
        if self._status in ("downloading", "uploading", "indexing") and self._task and not self._task.done():
            return {"ok": False, "message": "Đang có tiến trình upload khác đang chạy!"}

        link_type, resource_id = parse_gdrive_url(url)
        if link_type == "invalid":
            return {"ok": False, "message": "URL Google Drive hoặc link tải không hợp lệ."}

        client, client_type = await _get_upload_client()
        self._client_type = client_type

        self._cancel_requested = False
        self._status = "downloading"
        self._stage = "Đang khởi động kết nối..."
        self._current_file = ""
        self._file_index = 0
        self._total_files = 1
        self._download_percent = 0
        self._download_bytes = 0
        self._download_total = 0
        self._upload_percent = 0
        self._upload_bytes = 0
        self._upload_total = 0
        self._speed_str = ""
        self._error_message = ""
        self._start_time = time.time()
        self._end_time = 0.0
        self._logs = []
        self._uploaded_tracks = []
        self._channel_id = str(target_channel_id)

        client_label = "⚡ User Session (Tốc độ tối đa)" if client_type == "user_session" else "🤖 StreamBot"
        self._log(f"Bắt đầu upload lên kênh {target_channel_id} sử dụng {client_label}", "info")

        self._task = asyncio.create_task(
            self._run_upload_pipeline(
                url=url,
                link_type=link_type,
                resource_id=resource_id,
                target_channel_id=target_channel_id,
                default_artist=default_artist,
                default_album=default_album,
                auto_scrape=auto_scrape,
                send_as_document=send_as_document,
            )
        )
        return {
            "ok": True,
            "message": f"Đã khởi chạy tiến trình tải & upload bằng {client_label}.",
            "client_type": client_type
        }

    async def cancel(self) -> dict:
        if self._status not in ("downloading", "uploading", "indexing") or not self._task:
            return {"ok": False, "message": "Không có tiến trình nào đang chạy."}

        self._cancel_requested = True
        self._status = "cancelled"
        self._end_time = time.time()
        self._log("Tiến trình đã được dừng theo yêu cầu của bạn.", "warn")
        if self._task and not self._task.done():
            self._task.cancel()
        return {"ok": True, "message": "Đã hủy tiến trình tải lên."}

    async def _get_gdrive_file_info(self, file_id: str) -> Tuple[str, str]:
        """Trích xuất tiêu đề gốc và định dạng file từ trang xem trước Google Drive"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(f"https://drive.google.com/file/d/{file_id}/view", headers=headers)
                if r.status_code == 200:
                    m = re.search(r'<title>(.*?)</title>', r.text)
                    if m:
                        raw_title = m.group(1).replace(" - Google Drive", "").replace(" - Google Trang tính", "").strip()
                        raw_title = raw_title.replace("&quot;", '"').replace("&amp;", '&').replace("&lt;", '<').replace("&gt;", '>')
                        if raw_title and raw_title != "Google Drive":
                            return raw_title, r.text
        except Exception as e:
            LOGGER.debug(f"[GDRIVE VIEW FETCH] {e}")
        return f"gdrive_{file_id}", ""

    async def _download_gdrive_file(self, file_id: str, work_dir: str, known_filename: str = "") -> Optional[str]:
        """Tải một file Google Drive đơn lẻ với bộ nhớ đệm (Download Cache) và nhận diện lỗi Quota Exceeded"""
        
        # 1. Lấy thông tin & tên file gốc từ Google Drive Preview
        real_title, page_html = await self._get_gdrive_file_info(file_id)
        if known_filename:
            target_filename = known_filename
        elif real_title and "." in real_title:
            target_filename = real_title
        else:
            target_filename = f"gdrive_{file_id}"

        # 2. Kiểm tra trong Bộ nhớ đệm (Download Cache)
        try:
            for fname in os.listdir(CACHE_DOWNLOAD_DIR):
                if fname.startswith(f"{file_id}_") or (target_filename and fname.endswith(target_filename)):
                    c_path = os.path.join(CACHE_DOWNLOAD_DIR, fname)
                    if os.path.isfile(c_path) and os.path.getsize(c_path) > 4096:
                        cached_sz = os.path.getsize(c_path)
                        cached_fn = fname.split("_", 1)[-1] if "_" in fname else fname
                        self._log(f"⚡ Phát hiện file trong bộ nhớ đệm (Cache): '{cached_fn}' ({round(cached_sz/(1024*1024), 2)} MB). Bỏ qua bước tải Google Drive!", "success")
                        self._download_percent = 100
                        out_path = os.path.join(work_dir, cached_fn)
                        try:
                            shutil.copy2(c_path, out_path)
                            return out_path
                        except Exception:
                            return c_path
        except Exception as ex:
            LOGGER.debug(f"Cache check error: {ex}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        url_candidates = [
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t",
            f"https://docs.google.com/uc?export=download&id={file_id}&confirm=t",
            f"https://drive.google.com/uc?export=download&id={file_id}",
        ]

        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            resp = None
            download_url = None

            for u in url_candidates:
                try:
                    resp = await client.get(u, headers=headers)
                    if resp.status_code == 200:
                        download_url = u
                        break
                except Exception as e:
                    LOGGER.debug(f"Candidate {u} failed: {e}")

            if not resp or resp.status_code != 200:
                self._log(f"Không thể kết nối đến máy chủ Google Drive cho file '{target_filename}' (ID: {file_id})", "error")
                return None

            content_type = (resp.headers.get("content-type") or "").lower()

            # Kiểm tra nếu Google Drive trả về trang HTML (Lỗi Quota Exceeded, Cảnh báo Virus, hoặc Cần xác thực)
            if "text/html" in content_type or resp.text.startswith("<!DOCTYPE") or resp.text.startswith("<html"):
                html_body = resp.text
                
                # A. Phát hiện Quota Exceeded (Hết băng thông tải trong ngày của Google)
                if (
                    "Quota exceeded" in html_body or 
                    "vượt quá giới hạn" in html_body or 
                    "Too many users" in html_body or
                    "can't view or download" in html_body or
                    "can&#39;t view or download" in html_body or
                    "Sorry, you can" in html_body
                ):
                    err_msg = (
                        f"⚠️ Google Drive đã khóa tải file '{target_filename}' do vượt quá giới hạn lượt tải trong ngày (Google Quota Exceeded). "
                        f"Cách khắc phục ngay: Hãy mở link trên trình duyệt, chọn 'Tạo bản sao' (Make a copy) file này vào Google Drive của bạn rồi lấy link chia sẻ của bản sao đó để upload!"
                    )
                    self._error_message = err_msg
                    self._log(err_msg, "error")
                    return None

                # B. Phát hiện Token xác nhận tải file lớn (>100MB)
                confirm_match = (
                    re.search(r'confirm=([0-9A-Za-z_-]+)', html_body) or 
                    re.search(r'name="confirm"\s+value="([^"]+)"', html_body) or
                    re.search(r'id="uc-download-link"\s+href="([^"]+)"', html_body)
                )
                if confirm_match:
                    match_val = confirm_match.group(1)
                    if match_val.startswith("http"):
                        download_url = match_val
                    else:
                        download_url = f"https://docs.google.com/uc?export=download&confirm={match_val}&id={file_id}"
                    self._log(f"Đã xác thực token tải file lớn từ Google Drive cho '{target_filename}'...", "info")
                else:
                    # Kiểm tra xem có phải trang yêu cầu đăng nhập / quyền truy cập không
                    if "accounts.google.com" in str(resp.url) or "ServiceLogin" in html_body or "Access denied" in html_body:
                        err_msg = f"⚠️ File '{target_filename}' chưa được chia sẻ công khai. Vui lòng đặt quyền chia sẻ Google Drive là 'Bất kỳ ai có liên kết (Anyone with the link)'."
                        self._error_message = err_msg
                        self._log(err_msg, "error")
                        return None

            # 3. Stream tải file nhị phân trực tiếp vào Cache Folder
            final_dl_url = download_url or f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
            
            async with client.stream("GET", final_dl_url, headers=headers) as stream_resp:
                if stream_resp.status_code != 200:
                    self._log(f"Lỗi HTTP {stream_resp.status_code} khi tải nội dung file '{target_filename}'", "error")
                    return None

                header_fn = _extract_filename_from_headers(stream_resp.headers, "")
                if header_fn and header_fn != f"gdrive_{file_id}" and "." in header_fn:
                    final_filename = header_fn
                elif target_filename and "." in target_filename:
                    final_filename = target_filename
                else:
                    final_filename = header_fn or target_filename or f"gdrive_{file_id}.flac"

                content_len = stream_resp.headers.get("content-length")
                total_bytes = int(content_len) if content_len and content_len.isdigit() else 0

                self._download_total = total_bytes
                self._download_bytes = 0
                self._current_file = final_filename
                self._stage = f"Đang tải về từ Google Drive: {final_filename}"
                self._log(f"Bắt đầu tải: {final_filename} ({round(total_bytes/(1024*1024), 1) if total_bytes else '?'} MB)", "info")

                cache_path = os.path.join(CACHE_DOWNLOAD_DIR, f"{file_id}_{final_filename}")
                out_path = os.path.join(work_dir, final_filename)
                start_dl = time.time()
                last_update = 0

                with open(cache_path, "wb") as f_out:
                    async for chunk in stream_resp.aiter_bytes(chunk_size=1024 * 1024):
                        if self._cancel_requested:
                            return None
                        f_out.write(chunk)
                        self._download_bytes += len(chunk)

                        now = time.time()
                        if now - last_update > 0.5:
                            last_update = now
                            if total_bytes > 0:
                                self._download_percent = min(100, int((self._download_bytes / total_bytes) * 100))
                            elapsed_dl = now - start_dl
                            if elapsed_dl > 0:
                                mbps = (self._download_bytes / (1024 * 1024)) / elapsed_dl
                                self._speed_str = f"{mbps:.2f} MB/s"

                # 4. Kiểm tra file sau khi tải về
                downloaded_fsize = os.path.getsize(cache_path) if os.path.exists(cache_path) else 0
                if downloaded_fsize < 4096:
                    try:
                        with open(cache_path, "r", encoding="utf-8", errors="ignore") as f_chk:
                            chk_head = f_chk.read(500)
                            if "<!DOCTYPE" in chk_head or "<html" in chk_head:
                                if "Quota exceeded" in chk_head or "vượt quá giới hạn" in chk_head:
                                    err_msg = f"⚠️ File '{final_filename}' bị giới hạn lượt tải trong ngày (Google Drive Quota Exceeded). Hãy 'Tạo bản sao' trên Drive để tải."
                                else:
                                    err_msg = f"⚠️ File tải về '{final_filename}' không hợp lệ (Google Drive trả về trang HTML thông báo)."
                                self._error_message = err_msg
                                self._log(err_msg, "error")
                                if os.path.exists(cache_path):
                                    os.remove(cache_path)
                                return None
                    except Exception:
                        pass

                self._download_percent = 100
                self._log(f"✅ Tải thành công từ Google Drive: {final_filename} ({round(downloaded_fsize/(1024*1024), 2)} MB)", "success")
                
                # Sao chép vào work_dir
                try:
                    shutil.copy2(cache_path, out_path)
                    return out_path
                except Exception:
                    return cache_path

    async def _download_direct_url(self, url: str, work_dir: str) -> Optional[str]:
        """Tải file từ link trực tiếp (HTTP / HTTPS) có lưu Cache"""
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # Check cache
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        for fname in os.listdir(CACHE_DOWNLOAD_DIR):
            if fname.startswith(f"direct_{url_hash}_"):
                c_path = os.path.join(CACHE_DOWNLOAD_DIR, fname)
                if os.path.isfile(c_path) and os.path.getsize(c_path) > 4096:
                    cached_fn = fname.split("_", 2)[-1]
                    self._log(f"⚡ Phát hiện file trong cache: '{cached_fn}'. Bỏ qua bước tải lại!", "success")
                    self._download_percent = 100
                    out_path = os.path.join(work_dir, cached_fn)
                    try:
                        shutil.copy2(c_path, out_path)
                        return out_path
                    except Exception:
                        return c_path

        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code != 200:
                    self._log(f"Không thể tải từ URL (HTTP {resp.status_code})", "error")
                    return None

                file_name = _extract_filename_from_headers(resp.headers, os.path.basename(urllib.parse.urlparse(url).path) or "downloaded_audio")
                content_len = resp.headers.get("content-length")
                total_bytes = int(content_len) if content_len and content_len.isdigit() else 0

                self._download_total = total_bytes
                self._download_bytes = 0
                self._current_file = file_name
                self._stage = f"Đang tải file: {file_name}"
                self._log(f"Bắt đầu tải file: {file_name}", "info")

                cache_path = os.path.join(CACHE_DOWNLOAD_DIR, f"direct_{url_hash}_{file_name}")
                out_path = os.path.join(work_dir, file_name)
                start_dl = time.time()
                last_update = 0

                with open(cache_path, "wb") as f_out:
                    async for chunk in resp.aiter_bytes(chunk_size=1024 * 1024):
                        if self._cancel_requested:
                            return None
                        f_out.write(chunk)
                        self._download_bytes += len(chunk)

                        now = time.time()
                        if now - last_update > 0.5:
                            last_update = now
                            if total_bytes > 0:
                                self._download_percent = min(100, int((self._download_bytes / total_bytes) * 100))
                            elapsed_dl = now - start_dl
                            if elapsed_dl > 0:
                                mbps = (self._download_bytes / (1024 * 1024)) / elapsed_dl
                                self._speed_str = f"{mbps:.2f} MB/s"

                self._download_percent = 100
                self._log(f"✅ Tải thành công file: {file_name}", "success")
                try:
                    shutil.copy2(cache_path, out_path)
                    return out_path
                except Exception:
                    return cache_path

    async def _fetch_folder_file_ids(self, folder_id: str) -> List[Tuple[str, str]]:
        """Lấy danh sách các file trong Folder Google Drive công khai"""
        files = []
        try:
            url = f"https://drive.google.com/embeddedfolderview?id={folder_id}#list"
            headers = {"User-Agent": "Mozilla/5.0"}
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    html = resp.text
                    # Trích xuất các liên kết file trong trang folder
                    matches = re.findall(r'href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/[^"]*"[^>]*aria-label="([^"]+)"', html)
                    for fid, fname in matches:
                        files.append((fid, fname))
        except Exception as e:
            LOGGER.warning(f"[GDRIVE FOLDER SCRAPE] {e}")
        return files

    def _collect_audio_files(self, extract_dir: str) -> List[str]:
        """Duyệt đệ quy và gom tất cả file âm thanh trong thư mục"""
        audio_files = []
        for root, _, filenames in os.walk(extract_dir):
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    audio_files.append(os.path.join(root, fn))
        audio_files.sort()
        return audio_files

    async def _download_cover_image(self, cover_url: str, temp_dir: str) -> Optional[str]:
        """Tải ảnh bìa về làm thumbnail cho Telegram"""
        if not cover_url or not cover_url.startswith("http"):
            return None
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(cover_url)
                if r.status_code == 200:
                    cover_path = os.path.join(temp_dir, "thumb.jpg")
                    with open(cover_path, "wb") as f:
                        f.write(r.content)
                    return cover_path
        except Exception as e:
            LOGGER.debug(f"Cover download failed: {e}")
        return None

    async def _run_upload_pipeline(
        self,
        url: str,
        link_type: str,
        resource_id: str,
        target_channel_id: str,
        default_artist: str,
        default_album: str,
        auto_scrape: bool,
        send_as_document: bool,
    ):
        work_dir = tempfile.mkdtemp(prefix="gdrive_upload_", dir=TEMP_UPLOAD_DIR)
        try:
            client, client_type = await _get_upload_client()
            target_chat_id = int(target_channel_id) if target_channel_id.lstrip("-").isdigit() else target_channel_id

            files_to_upload: List[str] = []

            # 1. Xử lý tải về theo loại link
            if link_type == "folder":
                self._stage = f"Đang quét danh sách file trong thư mục Google Drive..."
                self._log(f"Đang duyệt Folder ID: {resource_id}...", "info")
                folder_items = await self._fetch_folder_file_ids(resource_id)
                if not folder_items:
                    self._status = "error"
                    self._error_message = "Không tìm thấy file nào trong thư mục Google Drive (Hãy đảm bảo thư mục được chia sẻ công khai 'Bất kỳ ai có liên kết')."
                    self._log(self._error_message, "error")
                    return

                self._total_files = len(folder_items)
                self._log(f"Tìm thấy {len(folder_items)} file trong thư mục Google Drive.", "info")

                for idx, (fid, fname) in enumerate(folder_items, 1):
                    if self._cancel_requested:
                        break
                    self._file_index = idx
                    dl_path = await self._download_gdrive_file(fid, work_dir)
                    if dl_path and os.path.exists(dl_path):
                        ext = os.path.splitext(dl_path)[1].lower()
                        if ext in AUDIO_EXTENSIONS:
                            files_to_upload.append(dl_path)
                        elif ext in ARCHIVE_EXTENSIONS:
                            # Giải nén đa định dạng (.rar, .7z, .zip, .tar)
                            sub_extract = os.path.join(work_dir, f"ext_{idx}")
                            success, extract_msg = await _extract_archive(dl_path, sub_extract)
                            if success:
                                self._log(f"✅ {extract_msg} ({fname})", "success")
                                files_to_upload.extend(self._collect_audio_files(sub_extract))
                            else:
                                self._log(f"Lỗi giải nén {fname}: {extract_msg}", "warn")

            elif link_type == "file":
                self._stage = "Đang tải file từ Google Drive..."
                dl_path = await self._download_gdrive_file(resource_id, work_dir)
                if not dl_path or not os.path.exists(dl_path):
                    self._status = "error"
                    if not self._error_message:
                        self._error_message = "Tải file từ Google Drive thất bại. Vui lòng kiểm tra quyền chia sẻ công khai của file."
                    return

                ext = os.path.splitext(dl_path)[1].lower()
                if ext in ARCHIVE_EXTENSIONS:
                    self._stage = "Đang giải nén tập tin album..."
                    self._log(f"Phát hiện file nén ({ext}), đang tự động giải nén trích xuất danh sách bài hát...", "info")
                    extract_dir = os.path.join(work_dir, "extracted")
                    success, extract_msg = await _extract_archive(dl_path, extract_dir)
                    if success:
                        self._log(f"✅ {extract_msg}", "success")
                        files_to_upload = self._collect_audio_files(extract_dir)
                    else:
                        self._status = "error"
                        self._error_message = f"Không thể giải nén file ({ext}): {extract_msg}"
                        self._log(self._error_message, "error")
                        return
                elif ext in AUDIO_EXTENSIONS:
                    files_to_upload = [dl_path]
                else:
                    self._status = "error"
                    self._error_message = f"Định dạng file ({ext}) không phải là âm thanh hoặc file nén được hỗ trợ."
                    self._log(self._error_message, "error")
                    return

            elif link_type == "direct":
                self._stage = "Đang tải file từ đường dẫn trực tiếp..."
                dl_path = await self._download_direct_url(resource_id, work_dir)
                if not dl_path or not os.path.exists(dl_path):
                    self._status = "error"
                    self._error_message = "Tải file trực tiếp thất bại."
                    self._log(self._error_message, "error")
                    return

                ext = os.path.splitext(dl_path)[1].lower()
                if ext in ARCHIVE_EXTENSIONS:
                    extract_dir = os.path.join(work_dir, "extracted")
                    success, extract_msg = await _extract_archive(dl_path, extract_dir)
                    if success:
                        self._log(f"✅ {extract_msg}", "success")
                        files_to_upload = self._collect_audio_files(extract_dir)
                elif ext in AUDIO_EXTENSIONS:
                    files_to_upload = [dl_path]

            if not files_to_upload:
                self._status = "error"
                self._error_message = "Không tìm thấy bất kỳ file âm thanh nào (FLAC, MP3, WAV, DSF, M4A,...) để tải lên."
                self._log(self._error_message, "error")
                return

            self._total_files = len(files_to_upload)
            self._log(f"Sẵn sàng upload {len(files_to_upload)} bài hát lên kênh Telegram...", "info")

            # 2. Bắt đầu Upload từng bài lên Telegram bằng Userbot / StreamBot
            self._status = "uploading"
            uploaded_messages = []

            for idx, file_path in enumerate(files_to_upload, 1):
                if self._cancel_requested:
                    break

                self._file_index = idx
                raw_filename = os.path.basename(file_path)
                clean_title = clean_audio_filename(raw_filename)
                fsize = os.path.getsize(file_path)
                fsize_mb = round(fsize / (1024 * 1024), 2)

                self._current_file = raw_filename
                self._stage = f"Đang upload [{idx}/{self._total_files}]: {raw_filename} ({fsize_mb} MB)"
                self._upload_percent = 0
                self._upload_bytes = 0
                self._upload_total = fsize

                # Phân tích ca sĩ & album
                artist_candidate = default_artist
                album_candidate = default_album
                title_candidate = clean_title

                # Thử tách Artist - Title từ tên file
                if " - " in clean_title:
                    parts = clean_title.split(" - ", 1)
                    if not artist_candidate:
                        artist_candidate = parts[0].strip()
                    title_candidate = parts[1].strip()

                cover_url = ""
                # Tìm metadata & ảnh bìa online nếu bật auto_scrape
                if auto_scrape:
                    try:
                        scraped = await fetch_music_metadata(
                            raw_title=title_candidate,
                            raw_artist=artist_candidate,
                            file_name=raw_filename
                        )
                        if scraped:
                            if scraped.get("title"): title_candidate = scraped["title"]
                            if scraped.get("artist") and not default_artist: artist_candidate = scraped["artist"]
                            if scraped.get("album") and not default_album: album_candidate = scraped["album"]
                            if scraped.get("cover_url"): cover_url = scraped["cover_url"]
                    except Exception as e:
                        LOGGER.debug(f"Metadata scrape note: {e}")

                # Tải ảnh thumbnail về nếu có
                thumb_path = await self._download_cover_image(cover_url, work_dir) if cover_url else None

                # Progress callback cho pyrogram
                start_up = time.time()
                last_up_time = 0

                def _progress_cb(current, total):
                    nonlocal last_up_time
                    self._upload_bytes = current
                    self._upload_total = total
                    if total > 0:
                        self._upload_percent = min(100, int((current / total) * 100))
                    now = time.time()
                    if now - last_up_time > 0.5:
                        last_up_time = now
                        elapsed = now - start_up
                        if elapsed > 0:
                            mbps = (current / (1024 * 1024)) / elapsed
                            self._speed_str = f"{mbps:.2f} MB/s"

                caption = f"🎵 {title_candidate}\n👤 {artist_candidate or 'Unknown Artist'}\n💿 {album_candidate or 'Single'}"

                sent_msg = None
                try:
                    # Gửi file âm thanh
                    ext = os.path.splitext(file_path)[1].lower()
                    if send_as_document or ext in (".dsf", ".dff", ".ape"):
                        sent_msg = await client.send_document(
                            chat_id=target_chat_id,
                            document=file_path,
                            caption=caption,
                            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                            force_document=True,
                            progress=_progress_cb
                        )
                    else:
                        sent_msg = await client.send_audio(
                            chat_id=target_chat_id,
                            audio=file_path,
                            caption=caption,
                            title=title_candidate,
                            performer=artist_candidate or None,
                            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                            progress=_progress_cb
                        )
                except FloodWait as fw:
                    self._log(f"Telegram yêu cầu chờ FloodWait {fw.value}s — đang tự động tạm dừng...", "warn")
                    await asyncio.sleep(fw.value + 1)
                    if send_as_document:
                        sent_msg = await client.send_document(
                            chat_id=target_chat_id,
                            document=file_path,
                            caption=caption,
                            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                            force_document=True,
                            progress=_progress_cb
                        )
                    else:
                        sent_msg = await client.send_audio(
                            chat_id=target_chat_id,
                            audio=file_path,
                            caption=caption,
                            title=title_candidate,
                            performer=artist_candidate or None,
                            thumb=thumb_path if thumb_path and os.path.exists(thumb_path) else None,
                            progress=_progress_cb
                        )
                except Exception as upload_err:
                    self._log(f"❌ Lỗi khi upload bài '{raw_filename}': {upload_err}", "error")
                    continue

                if sent_msg:
                    self._log(f"✅ Đã upload thành công lên Telegram: {title_candidate} (Msg #{sent_msg.id})", "success")
                    uploaded_messages.append((sent_msg, title_candidate, artist_candidate, album_candidate, cover_url, file_path))
                    self._uploaded_tracks.append({
                        "msg_id": sent_msg.id,
                        "title": title_candidate,
                        "artist": artist_candidate,
                        "album": album_candidate,
                        "size": f"{fsize_mb} MB"
                    })

                # Nghỉ nhẹ giữa các bài
                await asyncio.sleep(0.3)

            # 3. Lập chỉ mục vào Thư viện Nhạc
            if uploaded_messages:
                self._status = "indexing"
                self._stage = "Đang lập chỉ mục các bài hát vừa upload vào Thư viện Nhạc..."
                self._log(f"Đang đồng bộ {len(uploaded_messages)} bài hát mới vào Thư viện & MongoDB...", "info")
                await self._index_uploaded_tracks(uploaded_messages, target_chat_id)

            self._status = "completed"
            self._stage = "Hoàn tất upload toàn bộ bài hát!"
            self._end_time = time.time()
            self._log(f"🎉 Hoàn tất quá trình! Đã tải và upload thành công {len(uploaded_messages)}/{self._total_files} bài hát.", "success")

        except asyncio.CancelledError:
            self._status = "cancelled"
            self._end_time = time.time()
            self._log("Tiến trình đã bị dừng.", "warn")
        except Exception as exc:
            self._status = "error"
            self._error_message = str(exc)
            self._end_time = time.time()
            self._log(f"Lỗi: {exc}", "error")
            LOGGER.error(f"[GDRIVE UPLOAD PIPELINE ERROR] {exc}", exc_info=True)
        finally:
            # Dọn dẹp thư mục tạm
            try:
                if os.path.exists(work_dir):
                    shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    async def _index_uploaded_tracks(self, uploaded_items: list, chat_id: int):
        """Lập chỉ mục trực tiếp các bài hát vừa upload vào cơ sở dữ liệu thư viện nhạc"""
        try:
            from Backend.fastapi.routes.music_routes import (
                _db_load_library,
                _db_save_library,
                detect_audio_quality,
                detect_genre_from_track_info,
                GLOW_PRESETS,
                _format_size,
                _format_duration,
            )

            albums = await _db_load_library()
            if not isinstance(albums, list):
                albums = []

            for sent_msg, title, artist, album_name, cover_url, local_fpath in uploaded_items:
                fsize = os.path.getsize(local_fpath) if os.path.exists(local_fpath) else 0
                media = sent_msg.audio or sent_msg.document
                duration_sec = getattr(media, "duration", 0) if media else 0
                mime_type = getattr(media, "mime_type", "") if media else ""
                raw_fname = getattr(media, "file_name", "") or os.path.basename(local_fpath)

                format_str, quality_tier, _ = detect_audio_quality(
                    file_name=raw_fname,
                    mime_type=mime_type,
                    file_size_bytes=fsize,
                    duration_sec=duration_sec,
                    caption_text=sent_msg.caption or ""
                )

                final_artist = (artist or "Unknown Artist").strip()
                final_album = (album_name or "Single").strip().upper()
                final_title = title or clean_audio_filename(raw_fname)

                track_dict = {
                    "id": sent_msg.id,
                    "name": final_title,
                    "artist": final_artist,
                    "album": final_album,
                    "duration": _format_duration(duration_sec),
                    "duration_sec": duration_sec,
                    "size": _format_size(fsize),
                    "size_bytes": fsize,
                    "format": format_str,
                    "qualityTier": quality_tier,
                    "chatId": str(chat_id),
                    "msgId": sent_msg.id,
                    "previewUrl": f"/api/music/stream/{chat_id}/{sent_msg.id}",
                    "coverUrl": cover_url,
                    "year": time.strftime("%Y"),
                }
                track_dict["genre"] = detect_genre_from_track_info(track_dict)

                # Tìm album đích hoặc tạo mới
                target_album = next((a for a in albums if a.get("title", "").upper() == final_album), None)
                if not target_album:
                    color_preset = GLOW_PRESETS[len(albums) % len(GLOW_PRESETS)]
                    target_album = {
                        "id": f"tg-album-{re.sub(r'[^a-zA-Z0-9_-]', '-', final_album.lower())[:30]}",
                        "title": final_album,
                        "artist": final_artist.upper(),
                        "year": time.strftime("%Y"),
                        "format": format_str,
                        "totalSize": _format_size(fsize),
                        "publisher": f"{final_artist} / Telegram Cloud",
                        "coverUrl": cover_url,
                        "glowColors": color_preset,
                        "tracks": []
                    }
                    albums.insert(0, target_album)

                # Kiểm tra tránh trùng bài trong album
                existing_track = next((t for t in target_album.get("tracks", []) if int(t.get("msgId", 0)) == sent_msg.id), None)
                if not existing_track:
                    target_album["tracks"].append(track_dict)

            await _db_save_library(albums)
            self._log(f"Đã lưu và cập nhật {len(uploaded_items)} bài hát vào cơ sở dữ liệu!", "success")
        except Exception as e:
            LOGGER.error(f"[GDRIVE INDEX ERROR] {e}", exc_info=True)


gdrive_upload_manager = GoogleDriveUploadManager()
