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


def _apply_low_cpu_worker_limits() -> None:
    """Hạ ưu tiên và ghim worker nền vào một CPU logic khi hệ điều hành hỗ trợ."""
    if os.environ.get("MUSIC_SHAZAM_LOW_CPU") != "1":
        return

    cpu_count = max(1, os.cpu_count() or 1)
    target_cpu = cpu_count - 1

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.windll.kernel32
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            kernel32.GetProcessAffinityMask.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(ctypes.c_size_t),
                ctypes.POINTER(ctypes.c_size_t),
            ]
            kernel32.GetProcessAffinityMask.restype = wintypes.BOOL
            kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
            kernel32.SetProcessAffinityMask.restype = wintypes.BOOL

            process = kernel32.GetCurrentProcess()
            current_mask = ctypes.c_size_t(0)
            system_mask = ctypes.c_size_t(0)
            if kernel32.GetProcessAffinityMask(
                process,
                ctypes.byref(current_mask),
                ctypes.byref(system_mask),
            ):
                allowed_mask = current_mask.value or system_mask.value
                if allowed_mask:
                    # Chọn CPU logic cao nhất mà process hiện được phép dùng.
                    affinity_mask = 1 << (allowed_mask.bit_length() - 1)
                    kernel32.SetProcessAffinityMask(process, ctypes.c_size_t(affinity_mask))
        except Exception:
            pass
        return

    try:
        if hasattr(os, "sched_setaffinity"):
            if hasattr(os, "sched_getaffinity"):
                available_cpus = sorted(os.sched_getaffinity(0))
                if available_cpus:
                    target_cpu = available_cpus[-1]
            os.sched_setaffinity(0, {target_cpu})
    except Exception:
        pass
    try:
        os.nice(10)
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
    timeout_sec: float = 12.0,
    low_cpu: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Nhận diện tệp âm thanh qua Shazam một cách an toàn tuyệt đối.
    Nếu chạy trên Python 3.14, shazamio_core sẽ bị lỗi Access Violation (0xC0000005) do C-API binary,
    do đó hàm tự động cô lập truy vấn qua subprocess Python 3.11 mà không bao giờ làm sập máy chủ FastAPI.
    """
    if not file_path or not os.path.exists(file_path) or os.path.getsize(file_path) < 1024:
        return None

    direct_error = None

    # Nhận dạng thủ công có thể chạy trực tiếp để giảm overhead. Quét nền luôn
    # cô lập Shazam khỏi FastAPI vì phần tạo signature Rust có thể chiếm CPU.
    if not low_cpu and sys.version_info < (3, 14):
        try:
            from shazamio import Shazam
            shz = Shazam(language=language, endpoint_country=endpoint_country)
            out = await asyncio.wait_for(shz.recognize(file_path), timeout=timeout_sec)
            # Phản hồi hợp lệ nhưng không có track chỉ là "no match". Trước đây
            # code gọi lại chính đoạn đó qua subprocess, làm request tăng gấp đôi.
            return out or {}
        except asyncio.TimeoutError:
            # Timeout mạng không phải lỗi runtime của shazamio. Không chạy lại
            # cùng một request qua subprocess vì sẽ nhân đôi thời gian chờ.
            return {"_error": f"Timeout sau {timeout_sec:.0f}s"}
        except Exception as exc:
            direct_error = f"{type(exc).__name__}: {exc}"

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

    child_env = os.environ.copy()
    creationflags = 0
    if low_cpu:
        # Giới hạn các runtime native phổ biến về 1 worker. Một số bản
        # shazamio_core dùng Rust/native code nên giới hạn này giúp tránh
        # chiếm toàn bộ CPU khi scan nhiều bài liên tiếp.
        child_env.update({
            "MUSIC_SHAZAM_LOW_CPU": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "RAYON_NUM_THREADS": "1",
        })
        if os.name == "nt":
            creationflags |= getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_env,
            creationflags=creationflags,
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
                        if data and data.get("error"):
                            worker_error = str(data.get("error"))
                            if direct_error:
                                worker_error = f"{direct_error}; subprocess: {worker_error}"
                            return {"_error": worker_error}
                        # Worker chạy thành công nhưng Shazam không match.
                        return data or {}
                    except Exception:
                        pass
        if proc.returncode != 0:
            stderr_text = stderr_bytes.decode("utf-8", errors="ignore").strip() if stderr_bytes else ""
            err = stderr_text or f"subprocess exit code {proc.returncode}"
            if direct_error:
                err = f"{direct_error}; {err}"
            return {"_error": err}
    except asyncio.TimeoutError:
        # communicate() timeout không tự dừng tiến trình con. Dọn worker để
        # tránh tích tụ nhiều shazam subprocess khi mạng chậm/mất kết nối.
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=1.5)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except Exception:
            pass
        err = f"Timeout sau {timeout_sec:.0f}s"
        if direct_error:
            err = f"{direct_error}; {err}"
        return {"_error": err}
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        if direct_error:
            err = f"{direct_error}; {err}"
        return {"_error": err}

    if direct_error:
        return {"_error": direct_error}
    return None


async def _main_worker():
    """Hàm chạy độc lập bên trong tiến trình con Python 3.11."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Missing audio file argument"}))
        return

    file_path = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else "vi-VN"
    endpoint_country = sys.argv[3] if len(sys.argv) > 3 else "VN"
    _apply_low_cpu_worker_limits()

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
