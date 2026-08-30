import asyncio
import base64
import secrets
import time
from typing import Dict, Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pyrogram import Client, raw
from pyrogram.raw.functions.auth import ExportLoginToken
from pyrogram.raw.types.auth import LoginToken, LoginTokenSuccess, LoginTokenMigrateTo
from pyrogram.errors import SessionPasswordNeeded, FloodWait, RPCError, PasswordHashInvalid

from Backend import db
from Backend.config import Telegram
from Backend.logger import LOGGER

qr_auth_router = APIRouter(tags=["Telegram QR Authentication"])

# Active temporary QR login sessions: {session_id: {...}}
_ACTIVE_QR_SESSIONS: Dict[str, dict] = {}

# Active authenticated Telegram User Clients for music streaming: {user_id: Client}
_USER_CLIENT_POOL: Dict[str, Client] = {}


def get_user_client_pool() -> Dict[str, Client]:
    return _USER_CLIENT_POOL


async def get_user_tg_client(user_id: str) -> Optional[Client]:
    """
    Lấy hoặc khởi tạo Telegram Client riêng cho người dùng đã đăng nhập.
    Ưu tiên Client đang chạy trong pool, nếu chưa có thì khởi tạo từ session_string trong DB.
    """
    if not user_id:
        return None

    client = _USER_CLIENT_POOL.get(user_id)
    if client and getattr(client, "is_connected", False):
        return client

    try:
        coll = db.dbs["tracking"]["music_users"]
        user_doc = await coll.find_one({"_id": user_id})
        if not user_doc or not user_doc.get("telegram_session"):
            return None

        session_str = user_doc.get("telegram_session")
        user_client = Client(
            name=f"music_user_{user_id}",
            api_id=Telegram.API_ID,
            api_hash=Telegram.API_HASH,
            session_string=session_str,
            sleep_threshold=20,
            workers=4,
            max_concurrent_transmissions=6,
            no_updates=True,
            in_memory=True,
        )
        await user_client.start()
        _USER_CLIENT_POOL[user_id] = user_client
        LOGGER.info(f"[MUSIC USERBOT] Khởi động thành công User Telegram Client cho user '{user_id}'")
        return user_client
    except Exception as e:
        LOGGER.warning(f"[MUSIC USERBOT] Không thể khởi động User Telegram Client cho user '{user_id}': {e}")
        return None


async def close_user_tg_client(user_id: str):
    """Dừng và giải phóng client của user khi logout"""
    client = _USER_CLIENT_POOL.pop(user_id, None)
    if client:
        try:
            if getattr(client, "is_connected", False):
                await client.stop()
            LOGGER.info(f"[MUSIC USERBOT] Đã dừng Telegram Client của user '{user_id}'")
        except Exception:
            pass


async def _cleanup_expired_qr_sessions():
    """Tự động dọn dẹp các phiên QR tạm thời đã hết hạn"""
    now = time.time()
    expired_ids = [
        sid for sid, sdata in _ACTIVE_QR_SESSIONS.items()
        if now > sdata.get("expires_at", 0) + 30
    ]
    for sid in expired_ids:
        sdata = _ACTIVE_QR_SESSIONS.pop(sid, None)
        if sdata and sdata.get("client"):
            try:
                cl = sdata["client"]
                if getattr(cl, "is_connected", False):
                    await cl.disconnect()
            except Exception:
                pass


@qr_auth_router.post("/api/music/auth/telegram/qr/init")
async def init_telegram_qr_login():
    """
    Khởi tạo phiên MTProto tạm thời, gọi ExportLoginToken để lấy mã QR đăng nhập
    """
    await _cleanup_expired_qr_sessions()

    session_id = secrets.token_hex(16)
    temp_client = None

    try:
        temp_client = Client(
            name=f"qr_temp_{session_id}",
            api_id=Telegram.API_ID,
            api_hash=Telegram.API_HASH,
            in_memory=True,
            no_updates=True
        )
        await temp_client.connect()

        res = await temp_client.invoke(
            ExportLoginToken(
                api_id=Telegram.API_ID,
                api_hash=Telegram.API_HASH,
                except_ids=[]
            )
        )

        # Xử lý nếu Telegram yêu cầu chuyển Data Center (DC)
        if isinstance(res, LoginTokenMigrateTo):
            target_dc = res.dc_id
            LOGGER.info(f"[QR AUTH] Di chuyển MTProto DC sang DC {target_dc}")
            await temp_client.session.stop()
            temp_client.session.dc_id = target_dc
            await temp_client.connect()
            res = await temp_client.invoke(
                ExportLoginToken(
                    api_id=Telegram.API_ID,
                    api_hash=Telegram.API_HASH,
                    except_ids=[]
                )
            )

        if not isinstance(res, LoginToken):
            raise HTTPException(status_code=500, detail="Không nhận được LoginToken từ Telegram.")

        token_b64 = base64.urlsafe_b64encode(res.token).decode("ascii").rstrip("=")
        tg_url = f"tg://login?token={token_b64}"
        expires_at = res.expires
        expires_in = max(0, int(expires_at - time.time()))

        _ACTIVE_QR_SESSIONS[session_id] = {
            "client": temp_client,
            "token_bytes": res.token,
            "expires_at": expires_at,
            "status": "pending",
            "created_at": time.time(),
            "user_data": None
        }

        return {
            "status": "success",
            "session_id": session_id,
            "tg_url": tg_url,
            "expires_at": expires_at,
            "expires_in": expires_in
        }
    except FloodWait as fw:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        return JSONResponse(
            status_code=429,
            content={"status": "error", "message": f"Telegram yêu cầu đợi {fw.value}s trước khi tạo mã QR mới."}
        )
    except Exception as e:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        LOGGER.error(f"[QR AUTH INIT ERROR] {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Lỗi khởi tạo mã QR: {str(e)}"}
        )


async def _finalize_qr_login(user_client: Client, request: Request) -> dict:
    """Hoàn tất quá trình đăng nhập, lưu vào MongoDB và thiết lập phiên web"""
    user_me = await user_client.get_me()
    session_str = await user_client.export_session_string()

    user_id = f"tg_{user_me.id}"
    first_name = user_me.first_name or ""
    last_name = user_me.last_name or ""
    display_name = f"{first_name} {last_name}".strip() or user_me.username or f"User {user_me.id}"
    username = user_me.username or f"tg_{user_me.id}"
    avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_me.id}"

    # Cập nhật thông tin người dùng vào MongoDB
    coll = db.dbs["tracking"]["music_users"]
    user_doc = {
        "_id": user_id,
        "username": username,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "telegram_id": user_me.id,
        "telegram_session": session_str,
        "is_active": True,
        "auth_type": "telegram_qr",
        "last_login": time.time()
    }
    await coll.update_one(
        {"_id": user_id},
        {"$set": user_doc, "$setOnInsert": {"created_at": time.time()}},
        upsert=True
    )

    # Đăng ký Client vào user pool để phục vụ streaming trực tiếp
    _USER_CLIENT_POOL[user_id] = user_client

    # Thiết lập cookie session
    request.session["music_user_id"] = user_id
    request.session["music_username"] = username
    request.session["music_display_name"] = display_name
    request.session["music_avatar_url"] = avatar_url

    LOGGER.info(f"[QR AUTH SUCCESS] Người dùng '{display_name}' (ID: {user_me.id}) đã đăng nhập thành công qua Telegram QR!")

    return {
        "status": "success",
        "message": f"Chào mừng {display_name}!",
        "user": {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "telegram_id": user_me.id,
            "is_active": True,
            "auth_type": "telegram_qr"
        }
    }


@qr_auth_router.get("/api/music/auth/telegram/qr/status")
async def check_telegram_qr_status(session_id: str, request: Request):
    """
    Thăm dò trạng thái mã QR (Pending, Success, Needs_2FA, Expired)
    """
    sdata = _ACTIVE_QR_SESSIONS.get(session_id)
    if not sdata:
        return {"status": "expired", "message": "Phiên đăng nhập không tồn tại hoặc đã hết hạn."}

    if time.time() > sdata.get("expires_at", 0):
        return {"status": "expired", "message": "Mã QR đã hết hạn. Vui lòng làm mới."}

    if sdata.get("status") == "success" and sdata.get("user_data"):
        return sdata["user_data"]

    if sdata.get("status") == "needs_2fa":
        return {"status": "needs_2fa", "message": "Tài khoản có bật mật khẩu 2 lớp. Vui lòng nhập mật khẩu 2FA."}

    temp_client = sdata.get("client")
    if not temp_client:
        return {"status": "expired", "message": "Phiên làm việc đã bị hủy."}

    try:
        res = await temp_client.invoke(
            ExportLoginToken(
                api_id=Telegram.API_ID,
                api_hash=Telegram.API_HASH,
                except_ids=[]
            )
        )

        if isinstance(res, LoginTokenSuccess):
            # Người dùng đã quét và xác nhận thành công trên điện thoại!
            user_data = await _finalize_qr_login(temp_client, request)
            sdata["status"] = "success"
            sdata["user_data"] = user_data
            return user_data

        elif isinstance(res, LoginToken):
            sdata["expires_at"] = res.expires
            return {
                "status": "pending",
                "expires_in": max(0, int(res.expires - time.time()))
            }
    except SessionPasswordNeeded:
        sdata["status"] = "needs_2fa"
        return {"status": "needs_2fa", "message": "Tài khoản có bật mật khẩu 2 lớp. Vui lòng nhập mật khẩu 2FA."}
    except FloodWait as fw:
        return {"status": "pending", "message": f"Chờ phản hồi Telegram ({fw.value}s)..."}
    except Exception as e:
        LOGGER.warning(f"[QR STATUS POLL] {e}")
        return {"status": "pending", "message": "Đang chờ quét mã..."}


@qr_auth_router.post("/api/music/auth/telegram/qr/2fa")
async def verify_telegram_qr_2fa(payload: dict, request: Request):
    """
    Xác thực mật khẩu bảo vệ 2 lớp (2FA Cloud Password)
    """
    session_id = payload.get("session_id", "").strip()
    password = payload.get("password", "")

    if not session_id or not password:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu session_id hoặc mật khẩu 2FA."})

    sdata = _ACTIVE_QR_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Phiên đăng nhập đã hết hạn."})

    temp_client = sdata["client"]
    try:
        await temp_client.check_password(password)
        user_data = await _finalize_qr_login(temp_client, request)
        sdata["status"] = "success"
        sdata["user_data"] = user_data
        return user_data
    except PasswordHashInvalid:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Mật khẩu 2FA không chính xác."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi xác thực 2FA: {str(e)}"})
