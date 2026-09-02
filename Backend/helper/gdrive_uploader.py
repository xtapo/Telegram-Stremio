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
    parse_artist_and_title,
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


def _cleanup_old_temp_files(max_age_seconds: int = 3600):
    """
    Tự động dọn dẹp các thư mục tạm và file cache rác cũ hơn max_age_seconds (mặc định 1 tiếng).
    """
    now = time.time()
    try:
        if os.path.exists(TEMP_UPLOAD_DIR):
            for item in os.listdir(TEMP_UPLOAD_DIR):
                if item == "cached_downloads":
                    continue
                item_path = os.path.join(TEMP_UPLOAD_DIR, item)
                try:
                    if os.path.isdir(item_path):
                        mtime = os.path.getmtime(item_path)
                        if now - mtime > max_age_seconds:
                            shutil.rmtree(item_path, ignore_errors=True)
                            LOGGER.debug(f"[CLEANUP] Đã xóa thư mục tạm cũ: {item}")
                except Exception:
                    pass

        if os.path.exists(CACHE_DOWNLOAD_DIR):
            for item in os.listdir(CACHE_DOWNLOAD_DIR):
                item_path = os.path.join(CACHE_DOWNLOAD_DIR, item)
                try:
                    if os.path.isfile(item_path):
                        mtime = os.path.getmtime(item_path)
                        # Dọn các file cache rác tồn đọng quá 2 tiếng
                        if now - mtime > 7200:
                            os.remove(item_path)
                            LOGGER.debug(f"[CLEANUP] Đã dọn file cache cũ: {item}")
                except Exception:
                    pass
    except Exception as e:
        LOGGER.debug(f"[CLEANUP ERROR] {e}")


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


def parse_gdrive_urls(raw_text: str) -> List[Tuple[str, str, str]]:
    """
    Phân tích danh sách nhiều liên kết (nhập cách nhau bằng dấu phẩy ',', dòng mới, chấm phẩy ';', gạch đứng '|' hoặc khoảng trắng).
    Trả về danh sách các tuple: (link_type, resource_id, original_url)
    """
    if not raw_text:
        return []

    # 1. Thử tách trước theo các dấu phân cách thông dụng (dấu phẩy, chấm phẩy, dòng mới, gạch đứng)
    tokens = re.split(r'[\r\n,;|]+', raw_text.strip())
    
    # 2. Nếu sau khi tách mà vẫn có token chứa nhiều link dính liền cách nhau bằng khoảng trắng
    expanded_tokens = []
    for tok in tokens:
        tok_clean = tok.strip().strip("'\"`")
        if not tok_clean:
            continue
        if "http" in tok_clean and tok_clean.count("http") > 1:
            sub_toks = re.findall(r'https?://[^\s,;|\'\"`<>]+', tok_clean)
            expanded_tokens.extend(sub_toks)
        else:
            expanded_tokens.append(tok_clean)

    results = []
    seen = set()

    for t in expanded_tokens:
        t = t.strip().rstrip(',;.:)\'\"]')
        if not t or t in seen:
            continue
        l_type, r_id = parse_gdrive_url(t)
        if l_type != "invalid":
            seen.add(t)
            results.append((l_type, r_id, t))

    return results


def _sync_list_gdrive_folder(folder_url_or_id: str) -> List[dict]:
    """
    Quét danh sách tất cả các files/albums bên trong Google Drive Folder công khai.
    Trả về danh sách dict: [{'id': ..., 'name': ..., 'url': ...}]
    """
    if "drive.google.com" not in folder_url_or_id:
        folder_url = f"https://drive.google.com/drive/folders/{folder_url_or_id}"
    else:
        folder_url = folder_url_or_id

    # 1. Dùng gdown library (chuẩn xác và tối ưu nhất cho Google Drive Folder)
    try:
        import gdown
        items = gdown.download_folder(url=folder_url, skip_download=True, quiet=True)
        if items:
            result = []
            for item in items:
                fn = os.path.basename(getattr(item, "path", "")) or getattr(item, "name", "") or f"gdrive_{item.id}"
                result.append({
                    "id": item.id,
                    "name": fn,
                    "url": f"https://drive.google.com/file/d/{item.id}/view"
                })
            LOGGER.info(f"[GDRIVE FOLDER] gdown quét được {len(result)} files trong folder: {folder_url}")
            return result
    except Exception as ex:
        LOGGER.warning(f"[GDRIVE FOLDER] gdown note: {ex}")

    # 2. Fallback HTML regex scraping
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
        resp = httpx.get(folder_url, headers=headers, follow_redirects=True, timeout=15.0)
        if resp.status_code == 200:
            found_ids = list(dict.fromkeys(re.findall(r'drive\.google\.com/file/d/([a-zA-Z0-9_-]{25,})', resp.text)))
            if not found_ids:
                found_ids = list(dict.fromkeys(re.findall(r'\[\"([a-zA-Z0-9_-]{28,38})\"', resp.text)))
            if found_ids:
                return [{"id": fid, "name": f"gdrive_{fid}", "url": f"https://drive.google.com/file/d/{fid}/view"} for fid in found_ids]
    except Exception as ex2:
        LOGGER.warning(f"[GDRIVE FOLDER HTML] fallback error: {ex2}")

    return []


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

        parsed_links = parse_gdrive_urls(url)
        if not parsed_links:
            return {"ok": False, "message": "Không tìm thấy URL Google Drive hoặc link tải hợp lệ nào."}

        client, client_type = await _get_upload_client()
        self._client_type = client_type

        self._cancel_requested = False
        self._status = "downloading"
        self._stage = "Đang khởi động kết nối..."
        self._current_file = ""
        self._file_index = 0
        self._total_files = len(parsed_links)
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
        self._log(f"Phát hiện {len(parsed_links)} liên kết/thư mục cần xử lý.", "info")

        self._task = asyncio.create_task(
            self._run_upload_pipeline(
                raw_url=url,
                parsed_links=parsed_links,
                target_channel_id=target_channel_id,
                default_artist=default_artist,
                default_album=default_album,
                auto_scrape=auto_scrape,
                send_as_document=send_as_document,
            )
        )
        return {
            "ok": True,
            "message": f"Đã khởi chạy tiến trình tải & upload {len(parsed_links)} liên kết/thư mục bằng {client_label}.",
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
        except Exception:
            pass
        return "", ""

    async def _download_gdrive_file(self, file_id: str, work_dir: str, known_filename: str = "") -> Optional[str]:
        """
        Tải file từ Google Drive với hỗ trợ file lớn, tự động vượt trang cảnh báo virus,
        cơ chế Quota Exceeded và Download Cache.
        """
        real_title, page_html = await self._get_gdrive_file_info(file_id)
        if known_filename:
            target_filename = known_filename
        elif real_title and "." in real_title:
            target_filename = real_title
        else:
            target_filename = f"gdrive_{file_id}"

        # Kiểm tra trong Bộ nhớ đệm (Download Cache)
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

            if "text/html" in content_type or resp.text.startswith("<!DOCTYPE") or resp.text.startswith("<html"):
                html_body = resp.text
                if any(q in html_body for q in ["Quota exceeded", "vượt quá giới hạn", "Too many users", "can't view or download", "Sorry, you can"]):
                    err_msg = f"⚠️ File '{target_filename}' đã bị giới hạn tải trong ngày của Google Drive (Quota Exceeded)."
                    self._error_message = err_msg
                    self._log(err_msg, "error")
                    return None

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
                    if "accounts.google.com" in str(resp.url) or "ServiceLogin" in html_body or "Access denied" in html_body:
                        err_msg = f"⚠️ File '{target_filename}' chưa được chia sẻ công khai. Vui lòng đặt quyền chia sẻ Google Drive là 'Bất kỳ ai có liên kết (Anyone with the link)'."
                        self._error_message = err_msg
                        self._log(err_msg, "error")
                        return None

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
                last_dl_bytes = 0

                with open(cache_path, "wb") as f_out:
                    async for chunk in stream_resp.aiter_bytes(chunk_size=1024 * 1024):
                        if self._cancel_requested:
                            return None
                        f_out.write(chunk)
                        self._download_bytes += len(chunk)

                        now = time.time()
                        if now - last_update >= 0.5:
                            delta_t = now - last_update if last_update > 0 else (now - start_dl)
                            delta_b = self._download_bytes - last_dl_bytes if last_update > 0 else self._download_bytes
                            last_update = now
                            last_dl_bytes = self._download_bytes
                            if total_bytes > 0:
                                self._download_percent = min(100, int((self._download_bytes / total_bytes) * 100))
                            if delta_t > 0 and delta_b >= 0:
                                mbps = (delta_b / (1024 * 1024)) / delta_t
                                self._speed_str = f"{mbps:.2f} MB/s"

                downloaded_fsize = os.path.getsize(cache_path) if os.path.exists(cache_path) else 0
                if downloaded_fsize < 4096:
                    try:
                        with open(cache_path, "r", encoding="utf-8", errors="ignore") as f_chk:
                            chk_head = f_chk.read(500)
                            if "<!DOCTYPE" in chk_head or "<html" in chk_head:
                                if "Quota exceeded" in chk_head or "vượt quá giới hạn" in chk_head:
                                    err_msg = f"⚠️ File '{final_filename}' bị giới hạn lượt tải trong ngày (Google Drive Quota Exceeded)."
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
                self._log(f"✅ Tải thành công từ Google Drive: {final_filename} ({round(downloaded_fsize / (1024 * 1024), 2)} MB)", "success")
                return cache_path

    async def _download_direct_url(self, url: str, work_dir: str) -> Optional[str]:
        """Tải file từ link HTTP/HTTPS trực tiếp với bộ nhớ đệm"""
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        base_fn = os.path.basename(urllib.parse.urlparse(url).path) or f"download_{url_hash}"

        try:
            for fname in os.listdir(CACHE_DOWNLOAD_DIR):
                if fname.startswith(f"{url_hash}_") or (base_fn and fname.endswith(base_fn)):
                    c_path = os.path.join(CACHE_DOWNLOAD_DIR, fname)
                    if os.path.isfile(c_path) and os.path.getsize(c_path) > 4096:
                        cached_sz = os.path.getsize(c_path)
                        cached_fn = fname.split("_", 1)[-1] if "_" in fname else fname
                        self._log(f"⚡ Phát hiện file trong bộ nhớ đệm (Cache): '{cached_fn}' ({round(cached_sz/(1024*1024), 2)} MB). Bỏ qua tải trực tiếp!", "success")
                        self._download_percent = 100
                        return c_path
        except Exception:
            pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
        try:
            async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
                async with client.stream("GET", url, headers=headers) as stream_resp:
                    if stream_resp.status_code != 200:
                        self._log(f"Lỗi HTTP {stream_resp.status_code} khi tải link trực tiếp", "error")
                        return None

                    header_fn = _extract_filename_from_headers(stream_resp.headers, "")
                    final_filename = header_fn or base_fn

                    content_len = stream_resp.headers.get("content-length")
                    total_bytes = int(content_len) if content_len and content_len.isdigit() else 0

                    self._download_total = total_bytes
                    self._download_bytes = 0
                    self._current_file = final_filename
                    self._stage = f"Đang tải về: {final_filename}"
                    self._log(f"Bắt đầu tải trực tiếp: {final_filename} ({round(total_bytes/(1024*1024), 1) if total_bytes else '?'} MB)", "info")

                    cache_path = os.path.join(CACHE_DOWNLOAD_DIR, f"{url_hash}_{final_filename}")
                    start_dl = time.time()
                    last_update = 0
                    last_dl_bytes = 0

                    with open(cache_path, "wb") as f_out:
                        async for chunk in stream_resp.aiter_bytes(chunk_size=1024 * 1024):
                            if self._cancel_requested:
                                return None
                            f_out.write(chunk)
                            self._download_bytes += len(chunk)

                            now = time.time()
                            if now - last_update >= 0.5:
                                delta_t = now - last_update if last_update > 0 else (now - start_dl)
                                delta_b = self._download_bytes - last_dl_bytes if last_update > 0 else self._download_bytes
                                last_update = now
                                last_dl_bytes = self._download_bytes
                                if total_bytes > 0:
                                    self._download_percent = min(100, int((self._download_bytes / total_bytes) * 100))
                                if delta_t > 0 and delta_b >= 0:
                                    mbps = (delta_b / (1024 * 1024)) / delta_t
                                    self._speed_str = f"{mbps:.2f} MB/s"

                    self._download_percent = 100
                    dl_sz = os.path.getsize(cache_path) if os.path.exists(cache_path) else 0
                    self._log(f"✅ Tải thành công: {final_filename} ({round(dl_sz/(1024*1024), 2)} MB)", "success")
                    return cache_path
        except Exception as e:
            self._log(f"Lỗi khi tải trực tiếp: {e}", "error")
            return None

    def _collect_audio_files(self, extract_dir: str) -> List[str]:
        """Duyệt đệ quy và thu thập tất cả các file âm thanh trong thư mục đã giải nén"""
        audio_files = []
        for root, _, files in os.walk(extract_dir):
            for file in sorted(files):
                ext = os.path.splitext(file)[1].lower()
                if ext in AUDIO_EXTENSIONS:
                    audio_files.append(os.path.join(root, file))
        return audio_files

    async def _download_cover_image(self, cover_url: str, work_dir: str) -> Optional[str]:
        if not cover_url:
            return None
        try:
            cover_path = os.path.join(work_dir, "cover_thumb.jpg")
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                r = await client.get(cover_url)
                if r.status_code == 200:
                    with open(cover_path, "wb") as f:
                        f.write(r.content)
                    return cover_path
        except Exception as e:
            LOGGER.debug(f"Cover download failed: {e}")
        return None

    async def _run_upload_pipeline(
        self,
        raw_url: str,
        parsed_links: List[Tuple[str, str, str]],
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

            # 1. Mở rộng tất cả các link và thư mục thành hàng đợi (Queue) các tập tin cụ thể
            self._stage = "Đang quét và phân tích danh sách liên kết/thư mục..."
            items_queue = []

            for link_type, resource_id, original_url in parsed_links:
                if self._cancel_requested:
                    break

                if link_type == "folder":
                    self._log(f"📁 Đang quét Thư mục Google Drive: {original_url}", "info")
                    folder_files = await asyncio.to_thread(_sync_list_gdrive_folder, original_url)
                    if folder_files:
                        self._log(f"✅ Tìm thấy {len(folder_files)} tập tin/album trong thư mục Google Drive!", "success")
                        for ff in folder_files:
                            items_queue.append({
                                "link_type": "file",
                                "resource_id": ff["id"],
                                "known_filename": ff["name"],
                                "source_label": f"📁 {ff['name']}"
                            })
                    else:
                        self._log(f"⚠️ Không tìm thấy tập tin nào trong thư mục Google Drive (ID: {resource_id})", "warn")
                elif link_type == "file":
                    items_queue.append({
                        "link_type": "file",
                        "resource_id": resource_id,
                        "known_filename": "",
                        "source_label": original_url
                    })
                elif link_type == "direct":
                    items_queue.append({
                        "link_type": "direct",
                        "resource_id": resource_id,
                        "known_filename": "",
                        "source_label": original_url
                    })

            if not items_queue:
                self._status = "error"
                self._error_message = "Không tìm thấy bất kỳ tập tin nào hợp lệ để tải về."
                self._log(self._error_message, "error")
                return

            total_queue_items = len(items_queue)
            self._log(f"🚀 Bắt đầu xử lý hàng đợi gồm {total_queue_items} mục (tập tin/album)...", "info")
            uploaded_messages_all = []

            # 2. Xử lý tuần tự từng mục trong hàng đợi
            for q_idx, q_item in enumerate(items_queue, 1):
                if self._cancel_requested:
                    break

                q_link_type = q_item["link_type"]
                q_res_id = q_item["resource_id"]
                q_known_fn = q_item["known_filename"]
                q_label = q_item["source_label"]

                self._file_index = q_idx
                self._total_files = total_queue_items
                self._stage = f"[{q_idx}/{total_queue_items}] Đang tải: {q_known_fn or q_label}..."
                self._log(f"👉 [{q_idx}/{total_queue_items}] Bắt đầu xử lý: {q_known_fn or q_label}", "info")

                dl_path = None
                if q_link_type == "file":
                    dl_path = await self._download_gdrive_file(q_res_id, work_dir, known_filename=q_known_fn)
                elif q_link_type == "direct":
                    dl_path = await self._download_direct_url(q_res_id, work_dir)

                if not dl_path or not os.path.exists(dl_path):
                    self._log(f"⚠️ Bỏ qua mục [{q_idx}/{total_queue_items}] do tải về thất bại: {q_label}", "warn")
                    continue

                # 3. Giải nén (nếu là file nén) hoặc lấy trực tiếp file audio
                files_to_upload = []
                ext = os.path.splitext(dl_path)[1].lower()
                sub_extract_dir = os.path.join(work_dir, f"item_{q_idx}_extracted")

                if ext in ARCHIVE_EXTENSIONS:
                    self._stage = f"[{q_idx}/{total_queue_items}] Đang giải nén tập tin album: {os.path.basename(dl_path)}..."
                    self._log(f"Phát hiện file nén ({ext}), đang giải nén trích xuất danh sách bài hát...", "info")
                    success, extract_msg = await _extract_archive(dl_path, sub_extract_dir)
                    if success:
                        self._log(f"✅ {extract_msg}", "success")
                        files_to_upload = self._collect_audio_files(sub_extract_dir)
                    else:
                        self._log(f"⚠️ Lỗi giải nén {os.path.basename(dl_path)}: {extract_msg}", "warn")
                elif ext in AUDIO_EXTENSIONS:
                    files_to_upload = [dl_path]

                if not files_to_upload:
                    self._log(f"⚠️ Không tìm thấy bài hát nào trong {os.path.basename(dl_path)}", "warn")
                    continue

                self._log(f"Tìm thấy {len(files_to_upload)} bài hát trong mục [{q_idx}/{total_queue_items}]. Đang upload lên Telegram...", "info")
                uploaded_messages_item = []

                # 4. Upload từng bài hát trong item này lên Telegram
                for track_idx, file_path in enumerate(files_to_upload, 1):
                    if self._cancel_requested:
                        break

                    raw_filename = os.path.basename(file_path)
                    clean_title = clean_audio_filename(raw_filename)
                    fsize = os.path.getsize(file_path)
                    fsize_mb = round(fsize / (1024 * 1024), 2)

                    self._current_file = raw_filename
                    self._stage = f"[{q_idx}/{total_queue_items}] Đang upload bài [{track_idx}/{len(files_to_upload)}]: {raw_filename} ({fsize_mb} MB)"
                    self._upload_percent = 0
                    self._upload_bytes = 0
                    self._upload_total = fsize

                    parsed_artist, parsed_title, parsed_album = parse_artist_and_title(
                        raw_title="",
                        raw_artist=default_artist,
                        raw_album=default_album,
                        file_name=raw_filename
                    )
                    artist_candidate = parsed_artist or default_artist
                    title_candidate = parsed_title or clean_title
                    album_candidate = parsed_album or default_album

                    cover_url = ""
                    if auto_scrape:
                        try:
                            scraped = await fetch_music_metadata(
                                raw_title=title_candidate,
                                raw_artist=artist_candidate,
                                raw_album=album_candidate,
                                file_name=raw_filename,
                                default_artist=default_artist,
                                default_album=default_album,
                            )
                            if scraped:
                                if scraped.get("title"): title_candidate = scraped["title"]
                                if scraped.get("artist"): artist_candidate = scraped["artist"]
                                if scraped.get("album") and not default_album: album_candidate = scraped["album"]
                                if scraped.get("cover_url"): cover_url = scraped["cover_url"]
                        except Exception as e:
                            LOGGER.debug(f"Metadata scrape note: {e}")

                    thumb_path = await self._download_cover_image(cover_url, work_dir) if cover_url else None

                    start_up = time.time()
                    last_up_time = 0
                    last_bytes = 0

                    def _progress_cb(current, total):
                        nonlocal last_up_time, last_bytes
                        self._upload_bytes = current
                        self._upload_total = total
                        if total > 0:
                            self._upload_percent = min(100, int((current / total) * 100))
                        now = time.time()
                        if now - last_up_time >= 0.5:
                            delta_time = now - last_up_time if last_up_time > 0 else (now - start_up)
                            delta_bytes = current - last_bytes if last_up_time > 0 else current
                            last_up_time = now
                            last_bytes = current
                            if delta_time > 0 and delta_bytes >= 0:
                                mbps = (delta_bytes / (1024 * 1024)) / delta_time
                                self._speed_str = f"{mbps:.2f} MB/s"

                    caption = f"🎵 {title_candidate}\n👤 {artist_candidate or 'Unknown Artist'}\n💿 {album_candidate or 'Single'}"

                    sent_msg = None
                    try:
                        ext_f = os.path.splitext(file_path)[1].lower()
                        if send_as_document or ext_f in (".dsf", ".dff", ".ape"):
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
                        self._log(f"✅ Đã upload [{track_idx}/{len(files_to_upload)}]: {title_candidate} - {artist_candidate} (Msg #{sent_msg.id})", "success")
                        uploaded_messages_item.append((sent_msg, title_candidate, artist_candidate, album_candidate, cover_url, file_path))
                        self._uploaded_tracks.append({
                            "msg_id": sent_msg.id,
                            "title": title_candidate,
                            "artist": artist_candidate,
                            "album": album_candidate,
                            "size": f"{fsize_mb} MB"
                        })

                    # Nghỉ nhẹ an toàn giữa các bài để giữ tốc độ và tránh bị Telegram bóp băng thông
                    await asyncio.sleep(0.8)

                # 5. Đồng bộ các bài hát vừa upload vào Database MongoDB
                if uploaded_messages_item:
                    self._stage = f"Đang đồng bộ {len(uploaded_messages_item)} bài hát của mục [{q_idx}/{total_queue_items}] vào Thư viện..."
                    await self._index_uploaded_tracks(uploaded_messages_item, target_chat_id)
                    uploaded_messages_all.extend(uploaded_messages_item)

                # Dọn dẹp thư mục giải nén của mục này
                if os.path.exists(sub_extract_dir):
                    try:
                        shutil.rmtree(sub_extract_dir, ignore_errors=True)
                    except Exception:
                        pass

                # Xóa file cache của mục này sau khi đã hoàn thành upload
                try:
                    if os.path.exists(CACHE_DOWNLOAD_DIR):
                        for fname in os.listdir(CACHE_DOWNLOAD_DIR):
                            if fname.startswith(f"{q_res_id}_"):
                                c_file = os.path.join(CACHE_DOWNLOAD_DIR, fname)
                                if os.path.isfile(c_file):
                                    os.remove(c_file)
                except Exception:
                    pass

                # Thu hồi RAM chủ động sau mỗi album để tránh OOM Killer
                try:
                    import gc
                    gc.collect()
                except Exception:
                    pass

            self._status = "completed"
            self._stage = f"Hoàn tất upload toàn bộ {len(self._uploaded_tracks)} bài hát!"
            self._end_time = time.time()
            self._log(f"🎉 Hoàn tất toàn bộ tiến trình! Đã tải và upload thành công {len(self._uploaded_tracks)} bài hát từ {total_queue_items} mục.", "success")

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
            # 1. Dọn dẹp thư mục làm việc tạm
            try:
                if os.path.exists(work_dir):
                    shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

            # 2. Thu hồi RAM
            try:
                import gc
                gc.collect()
            except Exception:
                pass

            # 3. Quét dọn rác tự động các thư mục tạm cũ
            try:
                _cleanup_old_temp_files()
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
