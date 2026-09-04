import sys
import os
import json
import asyncio
import subprocess
import warnings
from typing import Optional, Dict, Any

warnings.filterwarnings("ignore", category=RuntimeWarning, module=r".*pydub.*")

# Bổ sung các thư mục chứa nhị phân chuẩn vào PATH môi trường
for _bin_d in ["/usr/bin", "/usr/local/bin", "/bin", "/usr/sbin", "/sbin"]:
    if os.path.exists(_bin_d) and _bin_d not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = f"{_bin_d}{os.pathsep}{os.environ.get('PATH', '')}"

try:
    import pydub
    from shutil import which
    _ff = which("ffmpeg") or ("/usr/bin/ffmpeg" if os.path.exists("/usr/bin/ffmpeg") else None)
    if _ff:
        pydub.AudioSegment.converter = _ff
except Exception:
    pass


def get_shazam_python() -> str:
    """Trả về trình thông dịch Python tương thích (Python 3.11/3.12) có cài shazamio để tránh crash trên 3.14."""
    if sys.version_info < (3, 14):
        try:
            import shazamio
            return sys.executable
        except Exception:
            pass

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    candidates = [
        os.path.join(base_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(base_dir, ".venv", "bin", "python"),
        os.path.expanduser(r"~\AppData\Roaming\uv\python\cpython-3.11-windows-x86_64-none\python.exe"),
        os.path.expanduser(r"~\AppData\Local\Programs\Python\Python312\python.exe"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return sys.executable


async def query_shazam_isolated(
    file_path: str,
    language: str = "vi-VN",
    endpoint_country: str = "VN",
    timeout_sec: float = 12.0
) -> Optional[Dict[str, Any]]:
    """
    Nhận diện tệp âm thanh qua Shazam một cách an toàn tuyệt đối.
    Nếu chạy trên Python 3.14, shazamio_core sẽ bị lỗi Access Violation (0xC0000005) do C-API binary,
    do đó hàm tự động cô lập truy vấn qua subprocess Python 3.11 mà không bao giờ làm sập máy chủ FastAPI.
    """
    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) < 1024:
        return None

    # Nếu Python hiện tại < 3.14 và có shazamio hoạt động được trong tiến trình:
    if sys.version_info < (3, 14):
        try:
            from shazamio import Shazam
            shz = Shazam(language=language, endpoint_country=endpoint_country)
            out = await asyncio.wait_for(shz.recognize(file_path), timeout=timeout_sec)
            if out and out.get("track"):
                return out
        except Exception:
            pass

    # Chạy qua subprocess độc lập bằng Python 3.11
    python_bin = get_shazam_python()
    script_path = os.path.abspath(__file__)
    cmd = [
        python_bin,
        "-u",
        script_path,
        os.path.abspath(file_path),
        language,
        endpoint_country
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        if proc.returncode == 0 and stdout_bytes:
            txt = stdout_bytes.decode("utf-8", errors="ignore").strip()
            # Tìm dòng JSON bắt đầu bằng { và kết thúc bằng }
            for line in reversed(txt.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        if data and data.get("track"):
                            return data
                    except Exception:
                        pass
    except Exception:
        pass

    return None


async def _main_worker():
    """Hàm chạy độc lập bên trong tiến trình con Python 3.11."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing audio file argument"}))
        return

    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "vi-VN"
    endpoint_country = sys.argv[3] if len(sys.argv) > 3 else "VN"

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    try:
        from shazamio import Shazam
        shz = Shazam(language=language, endpoint_country=endpoint_country)
        res = await shz.recognize(file_path)
        print(json.dumps(res or {}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(_main_worker())
