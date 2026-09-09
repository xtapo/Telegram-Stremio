from __future__ import annotations

import asyncio
import gzip
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import quote, urlparse
from zoneinfo import ZoneInfo

import httpx

from Backend import db
from Backend.helper.settings_manager import SettingsManager
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot


BACKUP_DIR = os.path.abspath(os.path.join("Music", "data", "backups"))
os.makedirs(BACKUP_DIR, exist_ok=True)
RUNS_COLLECTION = "scheduled_backup_runs"
SCHEDULED_PREFIX = "scheduled_"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _setting(name: str, default: Any = None) -> Any:
    return SettingsManager.current().to_dict().get(name, default)


def _safe_zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(str(name or "Asia/Ho_Chi_Minh"))
    except Exception:
        return ZoneInfo("Asia/Ho_Chi_Minh")


def _parse_hhmm(value: str) -> tuple[int, int]:
    try:
        hour, minute = str(value or "03:00").split(":", 1)
        hour_i, minute_i = int(hour), int(minute)
        if 0 <= hour_i <= 23 and 0 <= minute_i <= 59:
            return hour_i, minute_i
    except Exception:
        pass
    return 3, 0


def _next_run(settings: Dict[str, Any], now_utc: Optional[datetime] = None) -> Optional[datetime]:
    if not settings.get("scheduled_backup_enabled"):
        return None
    tz = _safe_zone(settings.get("scheduled_backup_timezone"))
    now = (now_utc or _utcnow()).astimezone(tz)
    hour, minute = _parse_hhmm(settings.get("scheduled_backup_time", "03:00"))
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    frequency = str(settings.get("scheduled_backup_frequency") or "daily").lower()
    if frequency == "weekly":
        weekday = max(0, min(6, int(settings.get("scheduled_backup_weekday", 0) or 0)))
        days_ahead = (weekday - now.weekday()) % 7
        candidate = candidate + timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
    elif candidate <= now:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _validate_backup_bytes(raw: bytes) -> Dict[str, Any]:
    if not raw:
        raise ValueError("Backup file is empty.")
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Backup root must be a JSON object.")
    if payload.get("app") != "Telegram-Stremio-Music":
        raise ValueError("Backup does not identify as Telegram-Stremio-Music.")
    for key in ("albums", "channels", "playlists", "artists_metadata"):
        if key not in payload or not isinstance(payload[key], list):
            raise ValueError(f"Backup section '{key}' is missing or invalid.")
    stats = payload.get("stats") or {}
    return {
        "created_at": payload.get("created_at"),
        "albums": len(payload["albums"]),
        "tracks": int(stats.get("tracks_count", 0) or 0),
        "channels": len(payload["channels"]),
        "playlists": len(payload["playlists"]),
        "artists": len(payload["artists_metadata"]),
    }


class ScheduledBackupManager:
    def __init__(self) -> None:
        self._task: Optional[asyncio.Task] = None
        self._wake = asyncio.Event()
        self._run_lock = asyncio.Lock()
        self._state: Dict[str, Any] = {
            "running": False,
            "last_status": "never",
            "last_error": "",
            "last_run_at": None,
            "last_filename": "",
            "next_run_at": None,
        }

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="scheduled-backup")

    def reschedule(self) -> None:
        self._wake.set()

    def status(self) -> Dict[str, Any]:
        settings = SettingsManager.current().to_dict()
        nxt = _next_run(settings)
        out = dict(self._state)
        out["next_run_at"] = nxt.isoformat() if nxt else None
        out["enabled"] = bool(settings.get("scheduled_backup_enabled"))
        out["destination"] = settings.get("scheduled_backup_destination", "telegram")
        return out

    async def _loop(self) -> None:
        while True:
            try:
                settings = SettingsManager.current().to_dict()
                nxt = _next_run(settings)
                self._state["next_run_at"] = nxt.isoformat() if nxt else None
                self._wake.clear()
                if nxt is None:
                    try:
                        await asyncio.wait_for(self._wake.wait(), timeout=60)
                    except asyncio.TimeoutError:
                        pass
                    continue

                delay = max(1.0, (nxt - _utcnow()).total_seconds())
                try:
                    await asyncio.wait_for(self._wake.wait(), timeout=delay)
                    continue
                except asyncio.TimeoutError:
                    pass
                await self.run_backup(reason="schedule")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.error(f"[SCHEDULED BACKUP] scheduler error: {exc}", exc_info=True)
                await asyncio.sleep(30)

    async def run_backup(self, reason: str = "manual") -> Dict[str, Any]:
        if self._run_lock.locked():
            raise RuntimeError("A scheduled backup is already running.")

        async with self._run_lock:
            self._state["running"] = True
            started = _utcnow()
            settings = SettingsManager.current().to_dict()
            destination = str(settings.get("scheduled_backup_destination") or "telegram").lower()
            filename = ""
            filepath = ""
            try:
                self._validate_destination(settings, destination)
                from Backend.fastapi.routes.music_routes import _build_music_backup_data

                data = await _build_music_backup_data()
                stamp = started.strftime("%Y%m%d_%H%M%S")
                filename = f"{SCHEDULED_PREFIX}{stamp}.json.gz"
                filepath = os.path.join(BACKUP_DIR, filename)
                raw = gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"), compresslevel=6)
                await asyncio.to_thread(self._write_file, filepath, raw)

                remote = await self._upload(destination, settings, filename, raw, filepath)
                run_doc = {
                    "destination": destination,
                    "filename": filename,
                    "size_bytes": len(raw),
                    "created_at": started,
                    "status": "success",
                    "reason": reason,
                    **remote,
                }
                await self._runs().insert_one(run_doc)
                await self._apply_retention(destination, settings)

                self._state.update({
                    "last_status": "success",
                    "last_error": "",
                    "last_run_at": started.isoformat(),
                    "last_filename": filename,
                })
                LOGGER.info(f"[SCHEDULED BACKUP] {destination} upload completed: {filename}")
                return {
                    "status": "success",
                    "message": f"Backup '{filename}' uploaded to {destination}.",
                    "filename": filename,
                    "size_kb": round(len(raw) / 1024, 1),
                    "remote": remote,
                }
            except Exception as exc:
                self._state.update({
                    "last_status": "error",
                    "last_error": str(exc),
                    "last_run_at": started.isoformat(),
                    "last_filename": filename,
                })
                LOGGER.error(f"[SCHEDULED BACKUP] failed: {exc}", exc_info=True)
                try:
                    await self._runs().insert_one({
                        "destination": destination,
                        "filename": filename,
                        "created_at": started,
                        "status": "error",
                        "reason": reason,
                        "error": str(exc),
                    })
                except Exception:
                    pass
                await self._notify_failure(settings, destination, str(exc))
                raise
            finally:
                self._state["running"] = False
                self.reschedule()

    async def test_restore(self) -> Dict[str, Any]:
        settings = SettingsManager.current().to_dict()
        destination = str(settings.get("scheduled_backup_destination") or "telegram").lower()
        record = await self._runs().find_one(
            {"destination": destination, "status": "success"},
            sort=[("created_at", -1)],
        )
        if not record:
            raise ValueError(f"No successful {destination} backup is available to test.")
        raw = await self._download(destination, settings, record)
        details = _validate_backup_bytes(raw)
        return {
            "status": "success",
            "message": f"Restore test passed for '{record.get('filename', '')}'. No live data was changed.",
            "filename": record.get("filename", ""),
            "details": details,
        }

    def _runs(self):
        tracking = db.dbs.get("tracking")
        if tracking is None:
            raise RuntimeError("Tracking database is not connected.")
        return tracking[RUNS_COLLECTION]

    @staticmethod
    def _write_file(path: str, raw: bytes) -> None:
        with open(path, "wb") as fh:
            fh.write(raw)

    @staticmethod
    def _validate_destination(settings: Dict[str, Any], destination: str) -> None:
        if destination not in {"telegram", "s3", "gdrive"}:
            raise ValueError("Destination must be telegram, s3, or gdrive.")
        if destination == "telegram" and not str(settings.get("scheduled_backup_telegram_chat_id") or "").strip():
            raise ValueError("Telegram backup chat ID is required.")
        if destination == "s3":
            required = ("scheduled_backup_s3_bucket", "scheduled_backup_s3_access_key", "scheduled_backup_s3_secret_key")
            missing = [k for k in required if not str(settings.get(k) or "").strip()]
            if missing:
                raise ValueError("S3 bucket, access key, and secret key are required.")
        if destination == "gdrive":
            required = (
                "scheduled_backup_gdrive_folder_id",
                "scheduled_backup_gdrive_client_id",
                "scheduled_backup_gdrive_client_secret",
                "scheduled_backup_gdrive_refresh_token",
            )
            missing = [k for k in required if not str(settings.get(k) or "").strip()]
            if missing:
                raise ValueError("Google Drive folder ID and OAuth client credentials/refresh token are required.")

    async def _upload(self, destination: str, settings: Dict[str, Any], filename: str, raw: bytes, filepath: str) -> Dict[str, Any]:
        if destination == "telegram":
            client, chat_id = self._telegram_client_and_chat(settings.get("scheduled_backup_telegram_chat_id"))
            msg = await client.send_document(
                chat_id=chat_id,
                document=filepath,
                caption=f"Scheduled backup\n{filename}\n{round(len(raw) / 1024, 1)} KB",
            )
            return {"remote_id": str(msg.id), "remote_ref": str(chat_id)}
        if destination == "s3":
            key = self._s3_key(settings, filename)
            await self._s3_request("PUT", settings, key, body=raw, content_type="application/gzip")
            return {"remote_id": key, "remote_ref": str(settings.get("scheduled_backup_s3_bucket") or "")}
        file_id = await self._gdrive_upload(settings, filename, raw)
        return {"remote_id": file_id, "remote_ref": str(settings.get("scheduled_backup_gdrive_folder_id") or "")}

    async def _download(self, destination: str, settings: Dict[str, Any], record: Dict[str, Any]) -> bytes:
        if destination == "telegram":
            target = record.get("remote_ref") or settings.get("scheduled_backup_telegram_chat_id")
            client, chat_id = self._telegram_client_and_chat(target)
            message = await client.get_messages(chat_id, int(record["remote_id"]))
            buf = await client.download_media(message, in_memory=True)
            if buf is None:
                raise RuntimeError("Telegram backup could not be downloaded.")
            return buf.getvalue()
        if destination == "s3":
            response = await self._s3_request("GET", settings, str(record["remote_id"]))
            return response.content
        return await self._gdrive_download(settings, str(record["remote_id"]))

    async def _delete_remote(self, destination: str, settings: Dict[str, Any], record: Dict[str, Any]) -> None:
        if destination == "telegram":
            target = record.get("remote_ref") or settings.get("scheduled_backup_telegram_chat_id")
            client, chat_id = self._telegram_client_and_chat(target)
            await client.delete_messages(chat_id, int(record["remote_id"]))
        elif destination == "s3":
            await self._s3_request("DELETE", settings, str(record["remote_id"]))
        else:
            await self._gdrive_delete(settings, str(record["remote_id"]))

    async def _apply_retention(self, destination: str, settings: Dict[str, Any]) -> None:
        days = int(settings.get("scheduled_backup_retention_days", 7) or 7)
        cutoff = _utcnow() - timedelta(days=max(1, days))
        old = await self._runs().find({
            "destination": destination,
            "status": "success",
            "created_at": {"$lt": cutoff},
        }).to_list(None)
        for record in old:
            try:
                await self._delete_remote(destination, settings, record)
                await self._runs().delete_one({"_id": record["_id"]})
            except Exception as exc:
                LOGGER.warning(f"[SCHEDULED BACKUP] retention could not delete {record.get('filename')}: {exc}")

        try:
            for name in os.listdir(BACKUP_DIR):
                if not name.startswith(SCHEDULED_PREFIX):
                    continue
                path = os.path.join(BACKUP_DIR, name)
                if datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < cutoff:
                    os.remove(path)
        except Exception as exc:
            LOGGER.warning(f"[SCHEDULED BACKUP] local retention cleanup failed: {exc}")

    async def _notify_failure(self, settings: Dict[str, Any], destination: str, error: str) -> None:
        target = str(settings.get("scheduled_backup_notification_chat_id") or "").strip()
        if not target and destination == "telegram":
            target = str(settings.get("scheduled_backup_telegram_chat_id") or "").strip()
        if not target:
            return
        try:
            client, chat_id = self._telegram_client_and_chat(target)
            await client.send_message(
                chat_id,
                f"Scheduled backup FAILED\nDestination: {destination}\nError: {error[:1000]}",
            )
        except Exception as exc:
            LOGGER.warning(f"[SCHEDULED BACKUP] failure notification could not be sent: {exc}")

    @staticmethod
    def _telegram_chat_id(value: Any) -> Any:
        text = str(value or "").strip()
        try:
            return int(text)
        except ValueError:
            return text

    @classmethod
    def _telegram_client_and_chat(cls, value: Any):
        text = str(value or "").strip()
        if text.casefold() in {"me", "saved messages", "saved_messages"}:
            client = botmod.Userbot
            if client is None or not getattr(client, "is_connected", False):
                raise RuntimeError(
                    "Telegram User Session is not connected. Sign in a Telegram user session before using 'me' for Saved Messages."
                )
            return client, "me"
        return StreamBot, cls._telegram_chat_id(text)

    @staticmethod
    def _s3_key(settings: Dict[str, Any], filename: str) -> str:
        prefix = str(settings.get("scheduled_backup_s3_prefix") or "telegram-stremio-backups").strip("/")
        return f"{prefix}/{filename}" if prefix else filename

    @staticmethod
    def _s3_url(settings: Dict[str, Any], key: str) -> str:
        region = str(settings.get("scheduled_backup_s3_region") or "us-east-1")
        endpoint = str(settings.get("scheduled_backup_s3_endpoint") or f"https://s3.{region}.amazonaws.com").rstrip("/")
        bucket = str(settings.get("scheduled_backup_s3_bucket") or "").strip()
        parsed = urlparse(endpoint)
        escaped_key = quote(key, safe="/-_.~")
        host = parsed.netloc
        base_path = parsed.path.rstrip("/")
        if host == "s3.amazonaws.com" or host.startswith("s3.") and host.endswith(".amazonaws.com"):
            return f"{parsed.scheme}://{bucket}.{host}{base_path}/{escaped_key}"
        return f"{endpoint}/{quote(bucket, safe='-_.~')}/{escaped_key}"

    async def _s3_request(
        self,
        method: str,
        settings: Dict[str, Any],
        key: str,
        body: bytes = b"",
        content_type: str = "application/octet-stream",
    ) -> httpx.Response:
        url = self._s3_url(settings, key)
        parsed = urlparse(url)
        region = str(settings.get("scheduled_backup_s3_region") or "us-east-1")
        access_key = str(settings.get("scheduled_backup_s3_access_key") or "")
        secret_key = str(settings.get("scheduled_backup_s3_secret_key") or "")
        now = _utcnow()
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        date_stamp = now.strftime("%Y%m%d")
        payload_hash = hashlib.sha256(body).hexdigest()
        canonical_uri = parsed.path or "/"
        canonical_headers = (
            f"host:{parsed.netloc}\n"
            f"x-amz-content-sha256:{payload_hash}\n"
            f"x-amz-date:{amz_date}\n"
        )
        signed_headers = "host;x-amz-content-sha256;x-amz-date"
        canonical_request = "\n".join([
            method.upper(), canonical_uri, "", canonical_headers, signed_headers, payload_hash
        ])
        credential_scope = f"{date_stamp}/{region}/s3/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256",
            amz_date,
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ])

        def sign(key_bytes: bytes, msg: str) -> bytes:
            return hmac.new(key_bytes, msg.encode("utf-8"), hashlib.sha256).digest()

        k_date = sign(("AWS4" + secret_key).encode("utf-8"), date_stamp)
        k_region = sign(k_date, region)
        k_service = sign(k_region, "s3")
        k_signing = sign(k_service, "aws4_request")
        signature = hmac.new(k_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
        authorization = (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}"
        )
        headers = {
            "Authorization": authorization,
            "Host": parsed.netloc,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
            "Content-Type": content_type,
        }
        async with httpx.AsyncClient(timeout=120, follow_redirects=False) as client:
            response = await client.request(method.upper(), url, content=body or None, headers=headers)
        if response.status_code not in (200, 201, 204):
            raise RuntimeError(f"S3 {method.upper()} failed ({response.status_code}): {response.text[:500]}")
        return response

    async def _gdrive_token(self, settings: Dict[str, Any]) -> str:
        data = {
            "client_id": str(settings.get("scheduled_backup_gdrive_client_id") or ""),
            "client_secret": str(settings.get("scheduled_backup_gdrive_client_secret") or ""),
            "refresh_token": str(settings.get("scheduled_backup_gdrive_refresh_token") or ""),
            "grant_type": "refresh_token",
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post("https://oauth2.googleapis.com/token", data=data)
        if response.status_code != 200:
            raise RuntimeError(f"Google OAuth refresh failed ({response.status_code}): {response.text[:500]}")
        token = response.json().get("access_token")
        if not token:
            raise RuntimeError("Google OAuth response did not include an access token.")
        return str(token)

    async def _gdrive_upload(self, settings: Dict[str, Any], filename: str, raw: bytes) -> str:
        token = await self._gdrive_token(settings)
        boundary = f"tgstremio_{secrets.token_hex(12)}"
        metadata = json.dumps({
            "name": filename,
            "parents": [str(settings.get("scheduled_backup_gdrive_folder_id") or "")],
        }).encode("utf-8")
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("utf-8")
            + metadata
            + f"\r\n--{boundary}\r\nContent-Type: application/gzip\r\n\r\n".encode("utf-8")
            + raw
            + f"\r\n--{boundary}--\r\n".encode("utf-8")
        )
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        }
        url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(url, content=body, headers=headers)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Google Drive upload failed ({response.status_code}): {response.text[:500]}")
        file_id = response.json().get("id")
        if not file_id:
            raise RuntimeError("Google Drive upload returned no file ID.")
        return str(file_id)

    async def _gdrive_download(self, settings: Dict[str, Any], file_id: str) -> bytes:
        token = await self._gdrive_token(settings)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{quote(file_id, safe='')}?alt=media"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url, headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Google Drive download failed ({response.status_code}): {response.text[:500]}")
        return response.content

    async def _gdrive_delete(self, settings: Dict[str, Any], file_id: str) -> None:
        token = await self._gdrive_token(settings)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://www.googleapis.com/drive/v3/files/{quote(file_id, safe='')}"
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.delete(url, headers=headers)
        if response.status_code not in (200, 204, 404):
            raise RuntimeError(f"Google Drive delete failed ({response.status_code}): {response.text[:500]}")


scheduled_backup_manager = ScheduledBackupManager()

