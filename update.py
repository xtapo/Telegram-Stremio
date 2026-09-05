from logging import FileHandler, StreamHandler, INFO, Formatter, basicConfig, error as log_error, info as log_info
from os import path as ospath, environ
from pathlib import Path
from subprocess import run as srun
from dotenv import load_dotenv
from datetime import datetime
import pytz
import shutil

IST = pytz.timezone("Asia/Kolkata")

class ISTFormatter(Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        return dt.strftime(datefmt or "%d-%b-%y %I:%M:%S %p")

log_file = "log.txt"
if ospath.exists(log_file):
    with open(log_file, "w") as f:
        f.truncate(0)
if Path(".git").exists():
    shutil.rmtree(".git")

file_handler = FileHandler(log_file)
stream_handler = StreamHandler()
formatter = ISTFormatter("[%(asctime)s] [%(levelname)s] - %(message)s", "%d-%b-%y %I:%M:%S %p")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)
basicConfig(handlers=[file_handler, stream_handler], level=INFO)

# ── Load config.env as the base (for DATABASE URI, etc.) ─────────────────────
load_dotenv("config.env")


def _fetch_upstream_from_db() -> tuple[str | None, str]:
    try:
        from pymongo import MongoClient
        raw_uris = environ.get("DATABASE", "")          
        uris = [u.strip() for u in raw_uris.replace(",", " ").split() if u.strip()]
        if not uris:
            log_info("update.py: No DATABASE found — skipping DB settings lookup.")
            return None, "master"

        tracking_uri = uris[0]
        client = MongoClient(tracking_uri, serverSelectionTimeoutMS=5000)
        doc = client["dbFyvio"]["settings"].find_one({"_id": "app_settings"})
        client.close()

        if doc:
            repo   = (doc.get("upstream_repo")   or "").strip() or None
            branch = (doc.get("upstream_branch") or "").strip() or "master"
            return repo, branch

    except Exception as exc:
        log_error(f"update.py: DB lookup failed ({exc}) — falling back to config.env.")

    return None, "master"


_packages_checked = False

def _ensure_linux_packages():
    """Tự động kiểm tra và cài đặt ffmpeg, p7zip, unrar nếu chạy trên môi trường Linux/Docker."""
    global _packages_checked
    if _packages_checked:
        return
    try:
        # Bổ sung các thư mục binary chuẩn vào PATH nếu thiếu
        for p in ["/usr/bin", "/usr/local/bin", "/bin", "/usr/sbin", "/sbin"]:
            if ospath.exists(p) and p not in environ.get("PATH", "").split(":"):
                environ["PATH"] = f"{p}:{environ.get('PATH', '')}"

        if shutil.which("apt-get"):
            missing = []
            if not (shutil.which("7z") or shutil.which("unrar") or ospath.exists("/usr/bin/7z")):
                missing.extend(["p7zip-full", "unrar-free"])
            if not (shutil.which("ffmpeg") or ospath.exists("/usr/bin/ffmpeg") or ospath.exists("/usr/local/bin/ffmpeg")):
                missing.append("ffmpeg")
            if missing:
                log_info(f"Linux/Docker environment: Auto-installing missing packages ({' '.join(missing)})...")
                srun(["apt-get", "update", "-y"])
                res = srun(["apt-get", "install", "-y"] + missing)
                if res.returncode == 0:
                    log_info(f"Linux/Docker environment: Successfully installed ({' '.join(missing)})!")
                else:
                    log_error(f"Linux/Docker environment: Failed to install packages (exit code {res.returncode})")
        _packages_checked = True
    except Exception as e:
        log_error(f"Package auto-install notice: {e}")


# ── Priority: config.env / ENV value  >  DB value ────────────────────────────
db_repo, db_branch = _fetch_upstream_from_db()

UPSTREAM_REPO   = environ.get("UPSTREAM_REPO",   "").strip() or db_repo or None
UPSTREAM_BRANCH = environ.get("UPSTREAM_BRANCH", "").strip() or db_branch or "master"

# ── Git update ────────────────────────────────────────────────────────────────
if UPSTREAM_REPO:
    if Path(".git").exists():
        srun(["rm", "-rf", ".git"])

    update_cmd = (
        f"git init -q && "
        f"git config --global user.email 'doc.adhikari@gmail.com' && "
        f"git config --global user.name 'weebzone' && "
        f"git add . && git commit -sm 'update' -q && "
        f"git remote add origin {UPSTREAM_REPO} && "
        f"git fetch origin -q && "
        f"git reset --hard origin/{UPSTREAM_BRANCH} -q"
    )

    update = srun(update_cmd, shell=True)
    repo = UPSTREAM_REPO.strip("/").split("/")
    repo_url = f"https://github.com/{repo[-2]}/{repo[-1]}"
    log_info(f"UPSTREAM_REPO: {repo_url} | UPSTREAM_BRANCH: {UPSTREAM_BRANCH}")

    if update.returncode == 0:
        log_info("Successfully updated with latest commits!!")
        commit_check = srun(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
        if commit_check.returncode == 0:
            log_info(f"Latest commit ID: {commit_check.stdout.strip()}")

        # Tự động cài đặt gói hệ thống nếu cần sau khi update repo
        _ensure_linux_packages()
    else:
        log_error("❌ Update failed! Retry or ask for support.")

# Đảm bảo các gói Linux cần thiết được cài đặt dù có UPSTREAM_REPO hay không
_ensure_linux_packages()



