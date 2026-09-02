import secrets
import time

from pyrogram import Client
from pyrogram.errors import (
    BadRequest,
    FloodWait,
    PasswordHashInvalid,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)

import Backend.pyrofork.bot as botmod
from Backend import db
from Backend.config import Telegram
from Backend.helper import global_search, task_manager
from Backend.helper.encrypt import decode_string, encode_string
from Backend.logger import LOGGER

_PENDING = {}
_PENDING_TTL = 600


async def _cleanup_pending():
    now = time.time()
    for lid in [k for k, v in _PENDING.items() if now - v["ts"] > _PENDING_TTL]:
        entry = _PENDING.pop(lid, None)
        if entry:
            try:
                await entry["client"].disconnect()
            except Exception:
                pass


def _profile(me) -> dict:
    name = " ".join(p for p in [me.first_name, me.last_name] if p) or "Telegram User"
    phone = me.phone_number or ""
    if phone and not phone.startswith("+"):
        phone = "+" + phone
    return {
        "name": name,
        "username": me.username or "",
        "phone": phone,
        "user_id": me.id,
    }


async def _store_session(session_string: str, profile: dict) -> None:
    encoded = await encode_string(session_string)
    user_id = profile.get("user_id")
    doc = {
        "session": encoded,
        "active": True,
        "created_at": time.time(),
        **profile,
    }
    # 1. Lưu vào collection danh sách multi-session
    if user_id:
        try:
            await db.dbs["tracking"]["user_sessions"].update_one(
                {"_id": str(user_id)}, {"$set": doc}, upsert=True
            )
        except Exception as e:
            LOGGER.debug(f"[MULTI SESSION DB] {e}")

    # 2. Lưu vào state user_session cho tương thích ngược (Primary)
    await db.dbs["tracking"]["state"].update_one(
        {"_id": "user_session"}, {"$set": doc}, upsert=True
    )


async def _read_stored() -> dict:
    return await db.dbs["tracking"]["state"].find_one({"_id": "user_session"}) or {}


async def get_all_stored_sessions() -> list:
    """Đọc toàn bộ danh sách các User Session đã lưu trong Database"""
    sessions = []
    try:
        cursor = db.dbs["tracking"]["user_sessions"].find({})
        async for doc in cursor:
            sessions.append(doc)
    except Exception as e:
        LOGGER.debug(f"[MULTI SESSIONS FETCH] {e}")

    if not sessions:
        legacy = await _read_stored()
        if legacy and legacy.get("session"):
            sessions.append(legacy)

    return sessions


async def get_active_session_string() -> str:
    doc = await _read_stored()
    if not doc or not doc.get("active") or not doc.get("session"):
        return ""
    try:
        return await decode_string(doc["session"])
    except Exception:
        return ""


async def _activate(session_string: str, user_id: int = None, profile: dict = None) -> Client:
    """Kích hoạt 1 Userbot Client và đăng ký vào multi_userbots pool"""
    try:
        uid = user_id or (profile.get("user_id") if profile else None)
        client = botmod.build_userbot(session_string, user_id=uid)
        if not getattr(client, "is_connected", False):
            await client.start()
        
        me = getattr(client, "me", None)
        if not me:
            try:
                me = await client.get_me()
            except Exception:
                pass
        
        if me:
            client.username = getattr(me, "username", None)
            actual_uid = me.id
            botmod.register_userbot(actual_uid, client)
            LOGGER.info(f"Userbot session activated: [@{client.username or actual_uid}] (ID: {actual_uid})")
        else:
            if uid:
                botmod.register_userbot(uid, client)

        for mod in (global_search, task_manager):
            try:
                mod._userbot_session_dead = False
            except Exception:
                pass

        return client
    except Exception as e:
        LOGGER.warning(f"[SESSION] Live Userbot activation failed: {e}")
        return None


async def _deactivate(user_id: int = None) -> None:
    """Dừng và giải phóng Userbot (hoặc toàn bộ Userbots nếu không chỉ định ID)"""
    if user_id and user_id in botmod.multi_userbots:
        client = botmod.unregister_userbot(user_id)
        if client:
            try:
                await client.stop()
            except Exception:
                pass
    else:
        for uid, cl in list(botmod.multi_userbots.items()):
            try:
                await cl.stop()
            except Exception:
                pass
        botmod.multi_userbots.clear()
        if botmod.Userbot is not None:
            try:
                await botmod.Userbot.stop()
            except Exception:
                pass
        botmod.Userbot = None


async def activate_all_stored_sessions() -> list:
    """Kích hoạt toàn bộ danh sách User Sessions khi khởi động máy chủ"""
    stored_list = await get_all_stored_sessions()
    activated = []

    for doc in stored_list:
        if not doc.get("active", True) or not doc.get("session"):
            continue
        try:
            raw_session = await decode_string(doc["session"])
            if not raw_session:
                continue
            uid = doc.get("user_id")
            client = await _activate(raw_session, user_id=uid, profile=doc)
            if client:
                activated.append(client)
        except Exception as e:
            LOGGER.warning(f"[STARTUP SESSION ACTIVATE] Error for user {doc.get('user_id')}: {e}")

    LOGGER.info(f"Multi-Userbot: Đã kích hoạt {len(activated)}/{len(stored_list)} User Sessions.")
    return activated


async def start_login(phone: str) -> dict:
    await _cleanup_pending()
    phone = (phone or "").strip()
    if not phone:
        raise ValueError("Enter a valid phone number with country code (e.g. +12025550123).")
    if not Telegram.API_ID or not Telegram.API_HASH:
        raise ValueError("API_ID / API_HASH are not configured.")

    client = Client(f"login_{secrets.token_hex(6)}", api_id=Telegram.API_ID, api_hash=Telegram.API_HASH, in_memory=True)
    await client.connect()
    try:
        sent = await client.send_code(phone)
    except (PhoneNumberInvalid, BadRequest):
        await client.disconnect()
        raise ValueError("That phone number was rejected by Telegram. Check the country code and try again.")
    except FloodWait as e:
        await client.disconnect()
        raise ValueError(f"Too many attempts. Try again in {e.value} seconds.")

    login_id = secrets.token_hex(12)
    _PENDING[login_id] = {"client": client, "phone": phone, "hash": sent.phone_code_hash, "ts": time.time()}
    return {"login_id": login_id}


async def submit_code(login_id: str, code: str) -> dict:
    entry = _PENDING.get(login_id)
    if not entry:
        raise ValueError("Login session expired. Start again.")
    client = entry["client"]
    code = (code or "").strip().replace(" ", "")
    try:
        await client.sign_in(entry["phone"], entry["hash"], code)
    except SessionPasswordNeeded:
        return {"status": "password_needed"}
    except PhoneCodeInvalid:
        raise ValueError("The code you entered is incorrect.")
    except PhoneCodeExpired:
        _PENDING.pop(login_id, None)
        try:
            await client.disconnect()
        except Exception:
            pass
        raise ValueError("The code has expired. Please request a new one.")
    return await _finalize(login_id)


async def submit_password(login_id: str, password: str) -> dict:
    entry = _PENDING.get(login_id)
    if not entry:
        raise ValueError("Login session expired. Start again.")
    client = entry["client"]
    try:
        await client.check_password((password or "").strip())
    except PasswordHashInvalid:
        raise ValueError("Incorrect two-step verification password.")
    return await _finalize(login_id)


async def _finalize(login_id: str) -> dict:
    entry = _PENDING.pop(login_id, None)
    client = entry["client"]
    me = await client.get_me()
    profile = _profile(me)
    session_string = await client.export_session_string()
    try:
        await client.disconnect()
    except Exception:
        pass
    await _store_session(session_string, profile)
    await _activate(session_string, user_id=profile["user_id"], profile=profile)
    return {"status": "ok", "profile": profile}


async def get_session_status() -> dict:
    doc = await _read_stored()
    multi = await get_multi_session_status()
    if not doc and multi["total_sessions"] == 0:
        return {"connected": False, "profile": None, "multi_sessions": multi}
    return {
        "connected": bool(doc.get("active") or multi["active_sessions"] > 0),
        "live": botmod.Userbot is not None or multi["active_sessions"] > 0,
        "profile": {
            "name": doc.get("name"),
            "username": doc.get("username"),
            "phone": doc.get("phone"),
            "user_id": doc.get("user_id"),
        },
        "multi_sessions": multi
    }


async def get_multi_session_status() -> dict:
    """Trả về trạng thái chi tiết của tất cả các User Sessions"""
    stored_list = await get_all_stored_sessions()
    sessions_info = []

    for doc in stored_list:
        uid = doc.get("user_id")
        uid_int = int(uid) if uid and str(uid).lstrip("-").isdigit() else None
        cl = botmod.multi_userbots.get(uid_int) if uid_int else None
        is_live = cl is not None and getattr(cl, "is_connected", False)

        sessions_info.append({
            "user_id": uid,
            "name": doc.get("name") or "Telegram User",
            "username": doc.get("username") or "",
            "phone": doc.get("phone") or "",
            "active": bool(doc.get("active", True)),
            "connected": is_live,
            "created_at": doc.get("created_at", 0),
            "is_primary": bool(botmod.Userbot == cl if cl else False)
        })

    active_count = sum(1 for s in sessions_info if s["connected"])
    return {
        "total_sessions": len(sessions_info),
        "active_sessions": active_count,
        "sessions": sessions_info
    }


async def disconnect_session(user_id: str = None) -> dict:
    if user_id:
        await db.dbs["tracking"]["user_sessions"].update_one(
            {"_id": str(user_id)}, {"$set": {"active": False}}
        )
        uid_int = int(user_id) if str(user_id).lstrip("-").isdigit() else None
        if uid_int:
            await _deactivate(user_id=uid_int)
    else:
        await db.dbs["tracking"]["state"].update_one({"_id": "user_session"}, {"$set": {"active": False}})
        await _deactivate()
    return {"ok": True}


async def reconnect_session(user_id: str = None) -> dict:
    if user_id:
        doc = await db.dbs["tracking"]["user_sessions"].find_one({"_id": str(user_id)})
        if not doc or not doc.get("session"):
            raise ValueError(f"Không tìm thấy session cho User ID {user_id}")
        session_str = await decode_string(doc["session"])
        if not session_str:
            raise ValueError("Không thể giải mã session string.")
        await db.dbs["tracking"]["user_sessions"].update_one(
            {"_id": str(user_id)}, {"$set": {"active": True}}
        )
        uid_int = int(user_id) if str(user_id).lstrip("-").isdigit() else None
        await _activate(session_str, user_id=uid_int, profile=doc)
    else:
        session_string = await get_active_session_string()
        if not session_string:
            raise ValueError("No stored session to reconnect.")
        await db.dbs["tracking"]["state"].update_one({"_id": "user_session"}, {"$set": {"active": True}})
        await _activate(session_string)
    return {"ok": True}


async def remove_session(user_id: str = None) -> dict:
    if user_id:
        uid_int = int(user_id) if str(user_id).lstrip("-").isdigit() else None
        if uid_int:
            await _deactivate(user_id=uid_int)
        await db.dbs["tracking"]["user_sessions"].delete_one({"_id": str(user_id)})
    else:
        await _deactivate()
        await db.dbs["tracking"]["state"].delete_one({"_id": "user_session"})
    return {"ok": True}
