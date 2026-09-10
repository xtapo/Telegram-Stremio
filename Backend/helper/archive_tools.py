"""Portable RAR backend for Linux installs updated without rebuilding the image."""
import hashlib
import io
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.request


_RELEASE = "26.03"
_ASSETS = {
    "x86_64": ("x64", "dc99eff5008f1ab79bd7084c68513701547a808a89502bf4133683535ab3c695"),
    "aarch64": ("arm64", "2389ba20e4d8295e8709c20b6263b69bd1ec4972fe38a04ad7a1badbf595b996"),
}
_INSTALL_LOCK = threading.Lock()
_retry_after = 0.0


def ensure_portable_7zip(cache_dir=None) -> str:
    """Install a verified standalone binary in writable app storage, without apt/root."""
    global _retry_after
    if platform.system() != "Linux":
        raise RuntimeError("Hãy cài 7-Zip hoặc UnRAR trên máy chạy ứng dụng.")
    asset = _ASSETS.get(platform.machine().lower())
    if asset is None:
        raise RuntimeError("Kiến trúc CPU này cần cài 7-Zip hoặc UnRAR thủ công.")
    arch, expected_sha = asset
    directory = Path(cache_dir or Path("Music") / "tools" / "7zip") / f"{_RELEASE}-{arch}"
    binary = directory.resolve() / "7zz"
    with _INSTALL_LOCK:
        if binary.is_file() and os.access(binary, os.X_OK):
            return str(binary)
        if time.monotonic() < _retry_after:
            raise RuntimeError("Lần tải công cụ trước thất bại; hãy thử lại sau một phút hoặc build lại image Docker.")
        try:
            url = f"https://github.com/ip7z/7zip/releases/download/{_RELEASE}/7z2603-linux-{arch}.tar.xz"
            with urllib.request.urlopen(url, timeout=30) as response:
                data = response.read(10 * 1024 * 1024 + 1)
            if hashlib.sha256(data).hexdigest() != expected_sha:
                raise RuntimeError("Gói 7-Zip không khớp SHA-256; không cài đặt.")
            binary.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="install-", dir=binary.parent) as staging:
                staged_binary = Path(staging) / "7zz"
                with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as archive:
                    # Copy only named regular files; never unpack arbitrary paths.
                    for name in ("7zz", "License.txt"):
                        member = archive.getmember(name)
                        if not member.isfile():
                            raise RuntimeError("Gói 7-Zip không hợp lệ.")
                        with archive.extractfile(member) as source, (Path(staging) / name).open("wb") as target:
                            shutil.copyfileobj(source, target)
                staged_binary.chmod(0o755)
                result = subprocess.run(
                    [str(staged_binary), "i"], stdin=subprocess.DEVNULL,
                    capture_output=True, text=True, errors="replace", timeout=15,
                )
                if result.returncode != 0 or "Rar5" not in result.stdout:
                    raise RuntimeError("7-Zip vừa tải không chạy được hoặc không hỗ trợ RAR5.")
                os.replace(Path(staging) / "License.txt", binary.parent / "License.txt")
                os.replace(staged_binary, binary)
            _retry_after = 0.0
            return str(binary)
        except Exception:
            _retry_after = time.monotonic() + 60
            raise
