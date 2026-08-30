import asyncio
import base64
import logging
import secrets
import time
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pyrogram import Client, raw
from pyrogram.errors import (
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    PhoneNumberUnoccupied,
    SessionPasswordNeeded,
)
from pyrogram.handlers import RawUpdateHandler
from pyrogram.raw.functions.auth import ExportLoginToken, ImportLoginToken
from pyrogram.raw.types.auth import LoginToken, LoginTokenMigrateTo, LoginTokenSuccess
from pyrogram.session import Auth, Session

from Backend import db
from Backend.config import Telegram

LOGGER = logging.getLogger(__name__)

qr_auth_router = APIRouter(tags=["Telegram Auth"])

# Quản lý các phiên Client tạm thời đang trong quá trình quét QR: session_id -> dict
_ACTIVE_QR_SESSIONS: Dict[str, dict] = {}

# Quản lý các phiên Client tạm thời đang trong quá trình đăng nhập SĐT: session_id -> dict
_ACTIVE_PHONE_SESSIONS: Dict[str, dict] = {}

# Quản lý các Client Telegram của người dùng sau khi đã đăng nhập thành công: user_id -> Client
_USER_CLIENT_POOL: Dict[str, Client] = {}


async def _migrate_and_import_token(client: Client, migrate_token: LoginTokenMigrateTo):
    """Di chuyển client sang đúng Data Center (DC) của người dùng và gọi ImportLoginToken"""
    current_res = migrate_token
    while isinstance(current_res, LoginTokenMigrateTo):
        target_dc = current_res.dc_id
        token = current_res.token
        LOGGER.info(f"[QR AUTH] Đang di chuyển client sang DC {target_dc} để hoàn tất ImportLoginToken...")
        try:
            await client.disconnect()
        except Exception:
            pass
        test_mode = await client.storage.test_mode()
        auth_key = await Auth(client, target_dc, test_mode).create()
        client.session = Session(client, target_dc, auth_key, test_mode)
        await client.storage.dc_id(target_dc)
        await client.storage.auth_key(auth_key)
        await client.connect()
        current_res = await client.invoke(ImportLoginToken(token=token))
    return current_res


async def get_user_tg_client(user_id: str) -> Optional[Client]:
    """
    Lấy hoặc khởi tạo Telegram Client cho user đã đăng nhập.
    Nếu Client đã có trong pool và đang kết nối thì trả về ngay.
    Nếu chưa, nạp session_string từ MongoDB và kết nối.
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

        session_str = user_doc["telegram_session"]
        new_client = Client(
            name=f"usr_session_{user_id}",
            session_string=session_str,
            api_id=Telegram.API_ID,
            api_hash=Telegram.API_HASH,
            in_memory=True,
            no_updates=True,
            app_version="XTAPO 2.6.0",
            device_model="XTAPO Web Player",
            system_version="Web Audio Engine",
            lang_code="vi"
        )
        await new_client.connect()
        _USER_CLIENT_POOL[user_id] = new_client
        LOGGER.info(f"[USER CLIENT POOL] Đã khởi tạo và kết nối Telegram Client cho user '{user_id}'")
        return new_client
    except Exception as e:
        LOGGER.error(f"[USER CLIENT POOL ERROR] Không thể khởi tạo Telegram Client cho user '{user_id}': {e}")
        return None


async def close_user_tg_client(user_id: str):
    """Đóng và xóa client khỏi pool khi user logout"""
    client = _USER_CLIENT_POOL.pop(user_id, None)
    if client and getattr(client, "is_connected", False):
        try:
            await client.disconnect()
            LOGGER.info(f"[USER CLIENT POOL] Đã ngắt kết nối Telegram Client của user '{user_id}'")
        except Exception as e:
            LOGGER.warning(f"[USER CLIENT POOL] Lỗi khi disconnect user '{user_id}': {e}")


async def _cleanup_expired_qr_sessions():
    """Dọn dẹp các phiên QR session đã hết hạn sau 3 phút"""
    now = time.time()
    expired_ids = [
        sid for sid, data in _ACTIVE_QR_SESSIONS.items()
        if now - data.get("created_at", 0) > 180
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
    và lắng nghe sự kiện quét mã UpdateLoginToken từ Telegram.
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
            app_version="XTAPO 2.6.0",
            device_model="XTAPO Web Player",
            system_version="Web Audio Engine",
            lang_code="vi"
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
        while isinstance(res, LoginTokenMigrateTo):
            target_dc = res.dc_id
            LOGGER.info(f"[QR AUTH] Di chuyển MTProto DC sang DC {target_dc}")
            try:
                await temp_client.disconnect()
            except Exception:
                pass
            temp_client.storage.dc_id = target_dc
            temp_client.storage.auth_key = None
            temp_client.session.dc_id = target_dc
            temp_client.session.auth_key = None
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
            "user_data": None,
            "last_active_check": 0  # Timestamp để throttle active check trong /status
        }

        # Best-effort: Đăng ký Raw Update Handler (có thể hoạt động nếu Dispatcher chạy)
        async def on_qr_raw_update(client, update, users, chats):
            try:
                if isinstance(update, raw.types.UpdateLoginToken):
                    LOGGER.info(f"[QR AUTH] Đã nhận tín hiệu quét mã UpdateLoginToken từ Telegram (Session: {session_id})")
                    login_res = await client.invoke(
                        ExportLoginToken(
                            api_id=Telegram.API_ID,
                            api_hash=Telegram.API_HASH,
                            except_ids=[]
                        )
                    )
                    if isinstance(login_res, LoginTokenMigrateTo):
                        login_res = await _migrate_and_import_token(client, login_res)
                    if isinstance(login_res, LoginTokenSuccess):
                        auth_user = getattr(login_res.authorization, "user", None)
                        if auth_user:
                            try:
                                client.storage.user_id = auth_user.id
                                client.storage.is_bot = False
                                client.storage.is_authorized = True
                            except Exception:
                                pass
                        user_data = await _finalize_qr_login(client, auth_user=auth_user)
                        _ACTIVE_QR_SESSIONS[session_id]["status"] = "success"
                        _ACTIVE_QR_SESSIONS[session_id]["user_data"] = user_data
            except SessionPasswordNeeded:
                LOGGER.info(f"[QR AUTH] Tài khoản cần xác thực 2FA (Session: {session_id})")
                _ACTIVE_QR_SESSIONS[session_id]["status"] = "needs_2fa"
            except Exception as ex:
                LOGGER.error(f"[QR RAW UPDATE ERROR] {ex}", exc_info=True)

        temp_client.add_handler(RawUpdateHandler(on_qr_raw_update))

        # Thử khởi động Dispatcher (best-effort, không chắc hoạt động cho non-authorized client)
        try:
            await temp_client.dispatcher.start()
        except Exception:
            pass

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


async def _finalize_qr_login(user_client: Client, auth_user=None) -> dict:
    """Hoàn tất quá trình đăng nhập, lưu vào MongoDB và trả về dữ liệu người dùng"""
    user_me = None
    try:
        user_me = await user_client.get_me()
    except Exception as e:
        LOGGER.warning(f"[QR AUTH] get_me() exception: {e}")

    if not user_me and auth_user:
        user_me = auth_user

    if not user_me:
        raise ValueError("Không thể lấy thông tin người dùng từ Telegram.")

    user_id = f"tg_{user_me.id}"
    first_name = getattr(user_me, "first_name", "") or ""
    last_name = getattr(user_me, "last_name", "") or ""
    display_name = f"{first_name} {last_name}".strip() or getattr(user_me, "username", "") or f"User {user_me.id}"
    username = getattr(user_me, "username", "") or f"tg_{user_me.id}"
    avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={user_me.id}"

    # Export session string
    session_str = ""
    try:
        session_str = await user_client.export_session_string()
    except Exception as e:
        LOGGER.warning(f"[QR AUTH] export_session_string failed: {e}")

    # Kiểm tra xem user có tham gia vào các Channel kho nhạc hay không
    is_channel_member = True
    channel_warning = None
    try:
        from Backend.fastapi.routes.music_routes import _db_load_library
        albums_data = await _db_load_library()
        if albums_data:
            sample_chat_ids = set()
            for alb in albums_data:
                for trk in alb.get("tracks", []):
                    cid = trk.get("chat_id") or trk.get("telegram_chat_id")
                    if cid:
                        sample_chat_ids.add(int(cid))
                    if len(sample_chat_ids) >= 3:
                        break
                if len(sample_chat_ids) >= 3:
                    break
            
            if sample_chat_ids:
                has_access = False
                for cid in sample_chat_ids:
                    try:
                        await user_client.get_chat(cid)
                        has_access = True
                        break
                    except Exception:
                        pass
                
                if not has_access:
                    is_channel_member = False
                    channel_warning = "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin"
    except Exception as e:
        LOGGER.warning(f"[QR AUTH] Kiểm tra channel membership: {e}")

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
        "is_channel_member": is_channel_member,
        "auth_type": "telegram_qr",
        "last_login": time.time()
    }
    await coll.update_one(
        {"_id": user_id},
        {"$set": user_doc, "$setOnInsert": {"created_at": time.time()}},
        upsert=True
    )

    # Đảm bảo music_user_data được khởi tạo
    data_coll = db.dbs["tracking"]["music_user_data"]
    await data_coll.update_one(
        {"_id": user_id},
        {"$setOnInsert": {"favorites": [], "playlists": [], "history": [], "settings": {}}},
        upsert=True
    )

    # Đăng ký Client vào user pool để phục vụ streaming trực tiếp
    _USER_CLIENT_POOL[user_id] = user_client

    LOGGER.info(f"[QR AUTH SUCCESS] Người dùng '{display_name}' (ID: {user_me.id}) đã đăng nhập thành công qua Telegram! Channel Member: {is_channel_member}")

    return {
        "status": "success",
        "message": f"Chào mừng {display_name}!",
        "is_channel_member": is_channel_member,
        "channel_warning": channel_warning,
        "user": {
            "id": user_id,
            "username": username,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "telegram_id": user_me.id,
            "is_active": True,
            "is_channel_member": is_channel_member,
            "channel_warning": channel_warning,
            "auth_type": "telegram_qr"
        }
    }


@qr_auth_router.get("/api/music/auth/telegram/qr/status")
async def check_telegram_qr_status(session_id: str, request: Request):
    """
    Thăm dò trạng thái mã QR (Pending, Success, Needs_2FA, Expired)
    Lắng nghe trạng thái từ RawUpdateHandler (không gọi ExportLoginToken lặp lại để tránh hủy token).
    """
    sdata = _ACTIVE_QR_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return {"status": "expired", "message": "Phiên đăng nhập không tồn tại hoặc đã hết hạn."}

    # Nếu đã thành công
    if sdata.get("status") == "success" and sdata.get("user_data"):
        user_info = sdata["user_data"].get("user", {})
        request.session["music_user_id"] = user_info.get("id")
        request.session["music_username"] = user_info.get("username")
        request.session["music_display_name"] = user_info.get("display_name")
        request.session["music_avatar_url"] = user_info.get("avatar_url")
        return sdata["user_data"]

    # Nếu đang ở trạng thái cần 2FA
    if sdata.get("status") == "needs_2fa":
        return {"status": "needs_2fa", "message": "Tài khoản có bật mật khẩu 2 lớp. Vui lòng nhập mật khẩu 2FA."}

    # Kiểm tra hạn sử dụng (cho phép thêm 5s buffer)
    expires_at = sdata.get("expires_at", 0)
    now = time.time()
    if now > expires_at + 5:
        sdata["status"] = "expired"
        return {"status": "expired", "message": "Mã QR đã hết hạn. Vui lòng làm mới."}

    return {
        "status": "pending",
        "expires_in": max(0, int(expires_at - now))
    }


@qr_auth_router.post("/api/music/auth/telegram/qr/check-now")
async def trigger_qr_check_now(payload: dict, request: Request):
    """Kiểm tra tức thì trạng thái sau khi người dùng quét mã trên điện thoại"""
    session_id = payload.get("session_id", "").strip()
    sdata = _ACTIVE_QR_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return {"status": "expired", "message": "Phiên đăng nhập đã hết hạn."}

    # Nếu auto-check đã phát hiện trạng thái, trả về ngay
    if sdata.get("status") == "needs_2fa":
        return {"status": "needs_2fa", "message": "Tài khoản có bật mật khẩu 2 lớp. Vui lòng nhập mật khẩu 2FA."}
    if sdata.get("status") == "success" and sdata.get("user_data"):
        user_info = sdata["user_data"].get("user", {})
        request.session["music_user_id"] = user_info.get("id")
        request.session["music_username"] = user_info.get("username")
        request.session["music_display_name"] = user_info.get("display_name")
        request.session["music_avatar_url"] = user_info.get("avatar_url")
        return sdata["user_data"]

    temp_client = sdata["client"]
    original_token = sdata.get("token_bytes")
    if not original_token:
        return {"status": "pending"}

    try:
        # Dùng ImportLoginToken với token gốc (KHÔNG gọi ExportLoginToken vì sẽ tạo token mới)
        login_res = await temp_client.invoke(
            ImportLoginToken(token=original_token)
        )
        if isinstance(login_res, LoginTokenMigrateTo):
            login_res = await _migrate_and_import_token(temp_client, login_res)

        if isinstance(login_res, LoginTokenSuccess):
            auth_user = getattr(login_res.authorization, "user", None)
            if auth_user:
                try:
                    temp_client.storage.user_id = auth_user.id
                    temp_client.storage.is_bot = False
                    temp_client.storage.is_authorized = True
                except Exception:
                    pass
            user_data = await _finalize_qr_login(temp_client, auth_user=auth_user)
            sdata["status"] = "success"
            sdata["user_data"] = user_data

            user_info = user_data.get("user", {})
            request.session["music_user_id"] = user_info.get("id")
            request.session["music_username"] = user_info.get("username")
            request.session["music_display_name"] = user_info.get("display_name")
            request.session["music_avatar_url"] = user_info.get("avatar_url")
            return user_data

    except SessionPasswordNeeded:
        LOGGER.info(f"[QR CHECK NOW] Tài khoản cần xác thực 2FA (Session: {session_id})")
        sdata["status"] = "needs_2fa"
        return {"status": "needs_2fa", "message": "Tài khoản có bật mật khẩu 2 lớp. Vui lòng nhập mật khẩu 2FA."}
    except Exception as e:
        LOGGER.warning(f"[QR CHECK NOW] Lỗi kiểm tra tức thì: {e}")

    return {"status": sdata.get("status", "pending")}


@qr_auth_router.post("/api/music/auth/telegram/qr/2fa")
async def verify_telegram_qr_2fa(payload: dict, request: Request):
    """
    Xác thực mật khẩu bảo vệ 2 lớp (2FA Cloud Password)
    Tự động hoàn tất di chuyển Data Center nếu cần trước khi kiểm tra mật khẩu.
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
        # Đảm bảo token và DC đã được đồng bộ bằng ImportLoginToken (KHÔNG dùng ExportLoginToken)
        try:
            original_token = sdata.get("token_bytes")
            if original_token:
                login_res = await temp_client.invoke(
                    ImportLoginToken(token=original_token)
                )
                if isinstance(login_res, LoginTokenMigrateTo):
                    await _migrate_and_import_token(temp_client, login_res)
        except SessionPasswordNeeded:
            pass
        except Exception:
            pass

        user_me = await temp_client.check_password(password)
        user_data = await _finalize_qr_login(temp_client, auth_user=user_me)
        
        user_info = user_data.get("user", {})
        request.session["music_user_id"] = user_info.get("id")
        request.session["music_username"] = user_info.get("username")
        request.session["music_display_name"] = user_info.get("display_name")
        request.session["music_avatar_url"] = user_info.get("avatar_url")

        sdata["status"] = "success"
        sdata["user_data"] = user_data
        return user_data
    except PasswordHashInvalid:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Mật khẩu 2FA không chính xác."})
    except Exception as e:
        LOGGER.error(f"[2FA ERROR] {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi xác thực 2FA: {str(e)}"})


# ─────────────────────────────────────────────────────────────────────────────
# ĐĂNG NHẬP THỦ CÔNG BẰNG SỐ ĐIỆN THOẠI (PHONE NUMBER AUTH)
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_phone(raw_phone: str) -> str:
    """Chuẩn hóa số điện thoại theo định dạng quốc tế E.164 (+84...)"""
    phone = "".join(c for c in (raw_phone or "").strip() if c.isdigit() or c == "+")
    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+84" + phone[1:]
        else:
            phone = "+" + phone
    return phone


async def _cleanup_expired_phone_sessions():
    """Dọn dẹp các phiên đăng nhập SĐT đã hết hạn sau 10 phút"""
    now = time.time()
    expired_ids = [
        sid for sid, data in _ACTIVE_PHONE_SESSIONS.items()
        if now - data.get("created_at", 0) > 600
    ]
    for sid in expired_ids:
        sdata = _ACTIVE_PHONE_SESSIONS.pop(sid, None)
        if sdata and sdata.get("client"):
            try:
                cl = sdata["client"]
                if getattr(cl, "is_connected", False):
                    await cl.disconnect()
            except Exception:
                pass


@qr_auth_router.post("/api/music/auth/telegram/phone/send-code")
async def send_telegram_phone_code(payload: dict):
    """
    Bước 1: Gửi mã xác thực OTP tới ứng dụng Telegram (hoặc SMS) theo số điện thoại
    """
    await _cleanup_expired_phone_sessions()

    raw_phone = payload.get("phone_number", "").strip()
    if not raw_phone:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng nhập số điện thoại."})

    phone = _normalize_phone(raw_phone)
    if len(phone) < 8 or len(phone) > 16:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Số điện thoại không hợp lệ (Ví dụ: +84987654321 hoặc 0987654321)."})

    session_id = secrets.token_hex(16)
    temp_client = None

    try:
        temp_client = Client(
            name=f"phone_temp_{session_id}",
            api_id=Telegram.API_ID,
            api_hash=Telegram.API_HASH,
            in_memory=True,
            app_version="XTAPO 2.6.0",
            device_model="XTAPO Web Player",
            system_version="Web Audio Engine",
            lang_code="vi"
        )
        await temp_client.connect()

        sent_code = await temp_client.send_code(phone)

        _ACTIVE_PHONE_SESSIONS[session_id] = {
            "client": temp_client,
            "phone_number": phone,
            "phone_code_hash": sent_code.phone_code_hash,
            "created_at": time.time()
        }

        return {
            "status": "success",
            "session_id": session_id,
            "phone_number": phone,
            "message": f"Mã xác thực đã được gửi tới ứng dụng Telegram của số {phone}."
        }
    except PhoneNumberInvalid:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        return JSONResponse(status_code=400, content={"status": "error", "message": "Số điện thoại không hợp lệ hoặc chưa đăng ký Telegram."})
    except PhoneNumberBanned:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        return JSONResponse(status_code=403, content={"status": "error", "message": "Số điện thoại này đã bị Telegram khóa."})
    except PhoneNumberUnoccupied:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        return JSONResponse(status_code=400, content={"status": "error", "message": "Số điện thoại chưa tạo tài khoản Telegram. Vui lòng đăng ký trước trên điện thoại."})
    except FloodWait as fw:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        return JSONResponse(status_code=429, content={"status": "error", "message": f"Telegram yêu cầu đợi {fw.value}s trước khi gửi lại mã mới."})
    except Exception as e:
        if temp_client:
            try: await temp_client.disconnect()
            except Exception: pass
        LOGGER.error(f"[PHONE AUTH SEND CODE ERROR] {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi gửi mã OTP: {str(e)}"})


@qr_auth_router.post("/api/music/auth/telegram/phone/verify-code")
async def verify_telegram_phone_code(payload: dict, request: Request):
    """
    Bước 2: Xác nhận mã OTP để đăng nhập
    """
    session_id = payload.get("session_id", "").strip()
    phone_code = str(payload.get("phone_code", "")).strip().replace(" ", "").replace("-", "")

    if not session_id or not phone_code:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng nhập đầy đủ mã xác thực OTP."})

    sdata = _ACTIVE_PHONE_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Phiên đăng nhập đã hết hạn. Vui lòng gửi lại mã."})

    temp_client = sdata["client"]
    phone = sdata["phone_number"]
    phone_code_hash = sdata["phone_code_hash"]

    try:
        user_me = await temp_client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=phone_code
        )

        user_data = await _finalize_qr_login(temp_client, auth_user=user_me)

        # Lưu session cookie
        user_info = user_data.get("user", {})
        request.session["music_user_id"] = user_info.get("id")
        request.session["music_username"] = user_info.get("username")
        request.session["music_display_name"] = user_info.get("display_name")
        request.session["music_avatar_url"] = user_info.get("avatar_url")

        _ACTIVE_PHONE_SESSIONS.pop(session_id, None)

        return user_data

    except SessionPasswordNeeded:
        # Tài khoản có bật 2FA
        return {
            "status": "needs_2fa",
            "session_id": session_id,
            "message": "Tài khoản của bạn đã bật xác thực 2 lớp (2FA). Vui lòng nhập mật khẩu Cloud Password."
        }
    except PhoneCodeInvalid:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Mã xác thực OTP không chính xác."})
    except PhoneCodeExpired:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Mã xác thực OTP đã hết hạn. Vui lòng lấy mã mới."})
    except FloodWait as fw:
        return JSONResponse(status_code=429, content={"status": "error", "message": f"Telegram yêu cầu đợi {fw.value}s."})
    except Exception as e:
        LOGGER.error(f"[PHONE AUTH VERIFY CODE ERROR] {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi xác thực: {str(e)}"})


@qr_auth_router.post("/api/music/auth/telegram/phone/2fa")
async def verify_telegram_phone_2fa(payload: dict, request: Request):
    """
    Bước 3: Xác thực mật khẩu 2 lớp cho đăng nhập số điện thoại
    """
    session_id = payload.get("session_id", "").strip()
    password = payload.get("password", "")

    if not session_id or not password:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng nhập mật khẩu 2FA."})

    sdata = _ACTIVE_PHONE_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Phiên đăng nhập đã hết hạn."})

    temp_client = sdata["client"]

    try:
        user_me = await temp_client.check_password(password)
        user_data = await _finalize_qr_login(temp_client, auth_user=user_me)

        # Lưu session cookie
        user_info = user_data.get("user", {})
        request.session["music_user_id"] = user_info.get("id")
        request.session["music_username"] = user_info.get("username")
        request.session["music_display_name"] = user_info.get("display_name")
        request.session["music_avatar_url"] = user_info.get("avatar_url")

        _ACTIVE_PHONE_SESSIONS.pop(session_id, None)

        return user_data

    except PasswordHashInvalid:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Mật khẩu 2FA không chính xác."})
    except Exception as e:
        LOGGER.error(f"[PHONE AUTH 2FA ERROR] {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Lỗi xác thực 2FA: {str(e)}"})


@qr_auth_router.post("/api/music/auth/telegram/phone/resend-code")
async def resend_telegram_phone_code(payload: dict):
    """
    Gửi lại mã OTP
    """
    session_id = payload.get("session_id", "").strip()
    sdata = _ACTIVE_PHONE_SESSIONS.get(session_id)
    if not sdata or not sdata.get("client"):
        return JSONResponse(status_code=400, content={"status": "error", "message": "Phiên làm việc đã hết hạn."})

    temp_client = sdata["client"]
    phone = sdata["phone_number"]
    phone_code_hash = sdata["phone_code_hash"]

    try:
        sent_code = await temp_client.resend_code(phone, phone_code_hash)
        sdata["phone_code_hash"] = sent_code.phone_code_hash
        return {"status": "success", "message": f"Đã gửi lại mã xác thực mới tới số {phone}."}
    except FloodWait as fw:
        return JSONResponse(status_code=429, content={"status": "error", "message": f"Vui lòng đợi {fw.value}s trước khi gửi lại."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": f"Không thể gửi lại mã: {str(e)}"})
