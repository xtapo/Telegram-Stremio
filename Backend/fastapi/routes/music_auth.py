import re
import time
import secrets
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response as PlainResponse
from Backend import db
from Backend.helper.passwords import hash_password, verify_password
from Backend.fastapi.security.credentials import require_auth

auth_router = APIRouter(tags=["Music Authentication"])

def extract_client_ip(request: Request) -> str:
    """Trích xuất địa chỉ IP chính xác của client từ các header proxy hoặc request client"""
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        parts = [p.strip() for p in x_forwarded.split(",")]
        if parts and parts[0]:
            return parts[0]
    x_real = request.headers.get("X-Real-IP")
    if x_real:
        return x_real.strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def parse_user_agent_details(user_agent: str, client_device_info: dict = None) -> dict:
    """Phân tích User-Agent và kết hợp thông tin client để trích xuất OS, Browser, Device Type"""
    ua = (user_agent or "").lower()
    client_info = client_device_info or {}
    
    # Xác định OS
    os_name = client_info.get("os")
    os_icon = "fa-solid fa-desktop"
    if not os_name:
        if "windows nt 10.0" in ua or "windows nt 11.0" in ua or "windows" in ua:
            os_name = "Windows"
            os_icon = "fa-brands fa-windows text-sky-400"
        elif "iphone" in ua:
            os_name = "iOS (iPhone)"
            os_icon = "fa-brands fa-apple text-slate-300"
        elif "ipad" in ua:
            os_name = "iPadOS (iPad)"
            os_icon = "fa-brands fa-apple text-slate-300"
        elif "macintosh" in ua or "mac os x" in ua:
            os_name = "macOS"
            os_icon = "fa-brands fa-apple text-slate-300"
        elif "android" in ua:
            os_name = "Android"
            os_icon = "fa-brands fa-android text-emerald-400"
        elif "linux" in ua:
            os_name = "Linux"
            os_icon = "fa-brands fa-linux text-amber-400"
        else:
            os_name = "Unknown OS"
            os_icon = "fa-solid fa-laptop text-text-secondary"
    else:
        os_low = os_name.lower()
        if "windows" in os_low:
            os_icon = "fa-brands fa-windows text-sky-400"
        elif "ios" in os_low or "iphone" in os_low or "ipad" in os_low or "apple" in os_low or "mac" in os_low:
            os_icon = "fa-brands fa-apple text-slate-300"
        elif "android" in os_low:
            os_icon = "fa-brands fa-android text-emerald-400"
        elif "linux" in os_low:
            os_icon = "fa-brands fa-linux text-amber-400"

    # Xác định Browser
    browser_name = client_info.get("browser")
    browser_icon = "fa-solid fa-globe"
    if not browser_name:
        if "telegram" in ua:
            browser_name = "Telegram Webview"
            browser_icon = "fa-brands fa-telegram text-sky-400"
        elif "edg/" in ua or "edge" in ua:
            browser_name = "Microsoft Edge"
            browser_icon = "fa-brands fa-edge text-blue-400"
        elif "opr/" in ua or "opera" in ua:
            browser_name = "Opera"
            browser_icon = "fa-brands fa-opera text-red-500"
        elif "chrome" in ua and "safari" in ua and "edg" not in ua:
            browser_name = "Google Chrome"
            browser_icon = "fa-brands fa-chrome text-amber-400"
        elif "safari" in ua and "chrome" not in ua:
            browser_name = "Apple Safari"
            browser_icon = "fa-brands fa-safari text-sky-400"
        elif "firefox" in ua:
            browser_name = "Mozilla Firefox"
            browser_icon = "fa-brands fa-firefox-browser text-orange-500"
        else:
            browser_name = "Web Browser"
            browser_icon = "fa-solid fa-globe text-primary"
    else:
        b_low = browser_name.lower()
        if "chrome" in b_low:
            browser_icon = "fa-brands fa-chrome text-amber-400"
        elif "safari" in b_low:
            browser_icon = "fa-brands fa-safari text-sky-400"
        elif "firefox" in b_low:
            browser_icon = "fa-brands fa-firefox-browser text-orange-500"
        elif "edge" in b_low:
            browser_icon = "fa-brands fa-edge text-blue-400"
        elif "telegram" in b_low:
            browser_icon = "fa-brands fa-telegram text-sky-400"

    # Device Type
    device_type = client_info.get("device_type")
    if not device_type:
        if "mobi" in ua or "iphone" in ua or "android" in ua:
            device_type = "Mobile"
        elif "ipad" in ua or "tablet" in ua:
            device_type = "Tablet"
        else:
            device_type = "Desktop"

    screen_res = client_info.get("screen", "")

    return {
        "os": os_name,
        "os_icon": os_icon,
        "browser": browser_name,
        "browser_icon": browser_icon,
        "device_type": device_type,
        "screen": screen_res,
        "user_agent": user_agent or ""
    }


def get_current_music_user(request: Request):
    return request.session.get("music_user_id")


async def require_music_auth(request: Request):
    user_id = request.session.get("music_user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng tính năng này.")
    
    # Kiểm tra xem user có bị khóa không
    coll = db.dbs["tracking"]["music_users"]
    user = await coll.find_one({"_id": user_id})
    if not user or user.get("is_active") is False:
        request.session.pop("music_user_id", None)
        request.session.pop("music_username", None)
        raise HTTPException(status_code=403, detail="Tài khoản của bạn đã bị khóa hoặc không tồn tại.")
    return user_id


@auth_router.post("/api/music/auth/heartbeat")
async def music_user_heartbeat(payload: dict, request: Request):
    """
    Client gửi heartbeat định kỳ (30s) hoặc khi thay đổi bài hát/trạng thái.
    Ghi nhận: trạng thái online, IP, thiết bị, bài hát đang nghe realtime.
    """
    user_id = request.session.get("music_user_id")
    if not user_id:
        return {"status": "guest", "message": "No active session"}

    try:
        now = time.time()
        client_ip = extract_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        client_device = payload.get("device_info", {})
        device_details = parse_user_agent_details(user_agent, client_device)

        # Hoạt động nghe nhạc
        track_info = payload.get("current_track")
        playback_state = payload.get("playback_state", "idle")  # "playing", "paused", "idle"

        current_activity = None
        if track_info:
            current_activity = {
                "title": track_info.get("title") or track_info.get("name") or "Đang nghe nhạc",
                "artist": track_info.get("artist") or "Không rõ ca sĩ",
                "album": track_info.get("album") or "",
                "cover_url": track_info.get("cover_url") or track_info.get("coverUrl") or "",
                "state": playback_state,
                "updated_at": now
            }

        coll = db.dbs["tracking"]["music_users"]
        
        # Session entry cho lịch sử
        session_entry = {
            "ip": client_ip,
            "device": f"{device_details['os']} • {device_details['browser']}",
            "device_type": device_details["device_type"],
            "last_active": now
        }

        # Cập nhật document user
        update_data = {
            "last_seen": now,
            "last_ip": client_ip,
            "device_info": device_details,
            "current_activity": current_activity
        }

        await coll.update_one(
            {"_id": user_id},
            {
                "$set": update_data,
                "$push": {
                    "recent_sessions": {
                        "$each": [session_entry],
                        "$slice": -10  # Giữ lại tối đa 10 phiên gần nhất
                    }
                }
            }
        )

        return {"status": "success", "user_id": user_id, "timestamp": now}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/auth/register")
async def register_music_user(payload: dict, request: Request):
    return JSONResponse(
        status_code=403, 
        content={
            "status": "error", 
            "message": "Tính năng tự đăng ký tài khoản đã bị tắt. Vui lòng liên hệ Quản trị viên để được cấp tài khoản."
        }
    )


@auth_router.post("/api/music/auth/login")
async def login_music_user(payload: dict, request: Request):
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Username và Password là bắt buộc."})

    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        
        if not user or not verify_password(password, user.get("password_hash", "")):
            return JSONResponse(status_code=401, content={"status": "error", "message": "Sai tài khoản hoặc mật khẩu."})

        if user.get("is_active") is False:
            return JSONResponse(status_code=403, content={"status": "error", "message": "Tài khoản của bạn đã bị tạm khóa bởi Quản trị viên."})

        request.session["music_user_id"] = user["_id"]
        request.session["music_username"] = user["username"]
        
        now = time.time()
        client_ip = extract_client_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        client_device = payload.get("device_info", {})
        device_details = parse_user_agent_details(user_agent, client_device)

        await coll.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "last_login": now,
                    "last_seen": now,
                    "last_ip": client_ip,
                    "device_info": device_details
                }
            }
        )
        
        return {
            "status": "success", 
            "message": "Đăng nhập thành công!", 
            "user": {
                "id": user["_id"], 
                "username": user["username"], 
                "display_name": user.get("display_name", user["username"]), 
                "avatar_url": user.get("avatar_url", ""),
                "is_active": user.get("is_active", True)
            }
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/auth/logout")
async def logout_music_user(request: Request):
    user_id = request.session.pop("music_user_id", None)
    request.session.pop("music_username", None)
    request.session.pop("music_display_name", None)
    request.session.pop("music_avatar_url", None)
    if user_id:
        try:
            coll = db.dbs["tracking"]["music_users"]
            await coll.update_one(
                {"_id": user_id},
                {"$set": {"last_seen": time.time() - 300, "current_activity": None}}
            )
        except Exception:
            pass
        try:
            from Backend.fastapi.routes.telegram_qr_auth import close_user_tg_client
            await close_user_tg_client(user_id)
        except Exception:
            pass
    return {"status": "success", "message": "Đã đăng xuất."}


@auth_router.get("/api/music/auth/profile")
async def get_music_profile(request: Request):
    user_id = request.session.get("music_user_id")
    if not user_id:
        return {"status": "guest", "user": None}
        
    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"_id": user_id})
        if not user or user.get("is_active") is False:
            request.session.pop("music_user_id", None)
            request.session.pop("music_username", None)
            return {"status": "guest", "user": None}
            
        is_member = user.get("is_channel_member")
        if is_member is None:
            if user.get("telegram_session"):
                try:
                    from Backend.fastapi.routes.telegram_qr_auth import get_user_tg_client
                    from Backend.fastapi.routes.music_routes import _db_load_library
                    user_cl = await get_user_tg_client(user_id)
                    if user_cl:
                        albums_data = await _db_load_library()
                        sample_chat_ids = set()
                        for alb in (albums_data or []):
                            for trk in alb.get("tracks", []):
                                cid = trk.get("chat_id") or trk.get("chatId") or trk.get("telegram_chat_id")
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
                                    await user_cl.get_chat(cid)
                                    has_access = True
                                    break
                                except Exception:
                                    pass
                            is_member = has_access
                            await coll.update_one({"_id": user_id}, {"$set": {"is_channel_member": is_member}})
                except Exception:
                    pass
            if is_member is None:
                is_member = True

        channel_warning = None if is_member else "Tài khoản của bạn chưa tham gia thành viên vui lòng liên hệ Admin"

        return {
            "status": "authenticated", 
            "user": {
                "id": user["_id"], 
                "username": user["username"], 
                "display_name": user.get("display_name", user["username"]),
                "avatar_url": user.get("avatar_url", ""),
                "is_active": user.get("is_active", True),
                "is_channel_member": is_member,
                "channel_warning": channel_warning,
                "auth_type": user.get("auth_type", "password")
            }
        }
    except Exception:
        return {"status": "guest", "user": None}


# ── USER DATA API (FAVORITES & PLAYLISTS) ──

@auth_router.get("/api/music/user/favorites")
async def get_user_favorites(user_id: str = Depends(require_music_auth)):
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        favorites = doc.get("favorites", []) if doc else []
        return {"status": "success", "favorites": favorites}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.post("/api/music/user/favorites/toggle")
async def toggle_user_favorite(payload: dict, user_id: str = Depends(require_music_auth)):
    chat_id = payload.get("chat_id")
    msg_id = payload.get("msg_id")
    if chat_id is None or msg_id is None:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu chat_id hoặc msg_id"})
        
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        if not doc:
            await coll.insert_one({"_id": user_id, "favorites": [], "playlists": [], "history": [], "settings": {}})
            doc = {"favorites": []}
            
        favorites = doc.get("favorites", [])
        target = next((f for f in favorites if str(f.get("chat_id")) == str(chat_id) and str(f.get("msg_id")) == str(msg_id)), None)
        
        is_favorite = False
        if target:
            favorites = [f for f in favorites if not (str(f.get("chat_id")) == str(chat_id) and str(f.get("msg_id")) == str(msg_id))]
        else:
            cid = int(chat_id) if str(chat_id).lstrip('-').isdigit() else str(chat_id)
            mid = int(msg_id) if str(msg_id).lstrip('-').isdigit() else str(msg_id)
            track_name = payload.get("name") or payload.get("title") or ""
            artist = payload.get("artist") or ""
            cover_url = payload.get("cover_url") or payload.get("coverUrl") or ""
            favorites.append({
                "chat_id": cid,
                "msg_id": mid,
                "title": track_name,
                "artist": artist,
                "cover_url": cover_url,
                "added_at": time.time()
            })
            is_favorite = True
            
        await coll.update_one({"_id": user_id}, {"$set": {"favorites": favorites}})
        return {"status": "success", "is_favorite": is_favorite, "message": "Đã thêm vào bài hát yêu thích ❤️" if is_favorite else "Đã xóa khỏi danh sách yêu thích 🤍"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.get("/api/music/user/playlists")
async def get_user_playlists(user_id: str = Depends(require_music_auth)):
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        playlists = doc.get("playlists", []) if doc else []
        return {"status": "success", "playlists": playlists}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.post("/api/music/user/playlists")
async def create_user_playlist(payload: dict, user_id: str = Depends(require_music_auth)):
    name = payload.get("name", "").strip()
    if not name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Vui lòng cung cấp tên Playlist."})
        
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        playlists = doc.get("playlists", []) if doc else []
        
        for p in playlists:
            if p.get("name", "").lower() == name.lower():
                return JSONResponse(status_code=409, content={"status": "error", "message": "Playlist đã tồn tại."})
                
        new_playlist = {
            "id": f"pl_{secrets.token_hex(8)}",
            "name": name,
            "tracks": [],
            "created_at": time.time()
        }
        playlists.append(new_playlist)
        
        await coll.update_one({"_id": user_id}, {"$set": {"playlists": playlists}}, upsert=True)
        return {"status": "success", "message": f"Đã tạo playlist '{name}'.", "playlist": new_playlist}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.put("/api/music/user/playlists/{playlist_id}")
async def update_user_playlist(playlist_id: str, payload: dict, user_id: str = Depends(require_music_auth)):
    tracks = payload.get("tracks")
    name = payload.get("name")
    
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        playlists = doc.get("playlists", []) if doc else []
        
        target = next((p for p in playlists if p.get("id") == playlist_id), None)
        if not target:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy playlist."})
            
        if tracks is not None:
            target["tracks"] = tracks
        if name is not None:
            target["name"] = name.strip()
            
        await coll.update_one({"_id": user_id}, {"$set": {"playlists": playlists}})
        return {"status": "success", "message": "Đã cập nhật playlist.", "playlist": target}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.delete("/api/music/user/playlists/{playlist_id}")
async def delete_user_playlist(playlist_id: str, user_id: str = Depends(require_music_auth)):
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        playlists = doc.get("playlists", []) if doc else []
        
        playlists = [p for p in playlists if p.get("id") != playlist_id]
        await coll.update_one({"_id": user_id}, {"$set": {"playlists": playlists}})
        return {"status": "success", "message": "Đã xóa playlist."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.get("/api/music/playlist/user/playlist/{playlist_id}.m3u8")
@auth_router.get("/api/music/playlist/user/playlist/{playlist_id}")
async def stream_user_playlist_m3u8(request: Request, playlist_id: str):
    """Xuất đường dẫn URL stream M3U8 trực tiếp cho Playlist cá nhân để mở bằng VLC, PotPlayer..."""
    base_url = str(request.base_url).rstrip("/")
    coll = db.dbs["tracking"]["music_user_data"]
    
    # Tìm playlist trong tất cả user data
    doc = await coll.find_one({"playlists.id": playlist_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Playlist not found")
        
    playlists = doc.get("playlists", [])
    target = next((p for p in playlists if p.get("id") == playlist_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Playlist not found")

    title = target.get("name", "Playlist")
    tracks = target.get("tracks", [])
    
    lines = ["#EXTM3U", "#EXTENC:UTF-8", f"#PLAYLIST:{title}\n"]
    for idx, t in enumerate(tracks):
        dur_str = str(t.get("duration", "0"))
        sec = -1
        if dur_str.isdigit():
            sec = int(dur_str)
        elif ":" in dur_str:
            parts = dur_str.split(":")
            if len(parts) == 2:
                sec = (int(parts[0]) if parts[0].isdigit() else 0) * 60 + (int(parts[1]) if parts[1].isdigit() else 0)

        name = t.get("name") or t.get("title") or f"Track {idx + 1}"
        artist = t.get("artist") or "XTAPO Music"
        chat_id = t.get("chat_id") or t.get("chatId")
        msg_id = t.get("msg_id") or t.get("msgId")
        preview_url = t.get("previewUrl") or t.get("url") or ""

        if chat_id and msg_id:
            stream_url = f"{base_url}/api/music/stream/{chat_id}/{msg_id}"
        elif preview_url:
            if preview_url.startswith("/"):
                stream_url = f"{base_url}{preview_url}"
            else:
                stream_url = preview_url
        else:
            continue

        lines.append(f"#EXTINF:{sec},{artist} - {name}")
        lines.append(stream_url)
        lines.append("")

    return PlainResponse(
        content="\n".join(lines),
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition(title, ".m3u8"),
            "Cache-Control": "public, max-age=120",
            "Access-Control-Allow-Origin": "*"
        }
    )


@auth_router.get("/api/music/playlist/user/favorites.m3u8")
@auth_router.get("/api/music/playlist/user/favorites")
async def stream_user_favorites_m3u8(request: Request, user_id: str = None, username: str = None):
    """Xuất đường dẫn URL stream M3U8 cho danh sách Bài Hát Yêu Thích"""
    from Backend.fastapi.routes.music_routes import _safe_content_disposition, _get_request_base_url
    base_url = _get_request_base_url(request)
    coll = db.dbs["tracking"]["music_user_data"]
    
    # Xác định user_id qua param hoặc session
    target_uid = user_id or request.session.get("music_user_id")
    if not target_uid and username:
        user_coll = db.dbs["tracking"]["music_users"]
        u = await user_coll.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        if u:
            target_uid = u["_id"]

    if not target_uid:
        # Nếu không có user_id, lấy danh sách đầu tiên hoặc báo lỗi
        doc = await coll.find_one({"favorites.0": {"$exists": True}})
    else:
        doc = await coll.find_one({"_id": target_uid})

    favorites = doc.get("favorites", []) if doc else []
    if not favorites:
        raise HTTPException(status_code=404, detail="No favorites found")

    lines = ["#EXTM3U", "#EXTENC:UTF-8", "#PLAYLIST:XTAPO_Favorite_Tracks\n"]
    for idx, f in enumerate(favorites):
        name = f.get("title") or f"Favorite Track {idx + 1}"
        artist = f.get("artist") or "XTAPO Music"
        cid = f.get("chat_id")
        mid = f.get("msg_id")
        stream_url = f"{base_url}/api/music/stream/{cid}/{mid}"
        lines.append(f"#EXTINF:210,{artist} - {name}")
        lines.append(stream_url)
        lines.append("")

    return PlainResponse(
        content="\n".join(lines),
        media_type="audio/x-mpegurl; charset=utf-8",
        headers={
            "Content-Disposition": _safe_content_disposition("XTAPO_Favorite_Tracks", ".m3u8"),
            "Cache-Control": "public, max-age=120",
            "Access-Control-Allow-Origin": "*"
        }
    )


# ── Quản Lý Users (Dành cho Admin) ─────────────────────────────────────────

@auth_router.get("/api/music/admin/users")
async def get_all_music_users(_: bool = Depends(require_auth)):
    """Lấy danh sách tất cả music users kèm trạng thái online, thiết bị, IP, bài hát đang nghe và dữ liệu cá nhân"""
    try:
        users = []
        user_coll = db.dbs["tracking"]["music_users"]
        data_coll = db.dbs["tracking"]["music_user_data"]
        now = time.time()
        online_count = 0
        
        cursor = user_coll.find().sort("created_at", -1)
        async for doc in cursor:
            doc.pop("password_hash", None)
            u_id = doc["_id"]
            
            # Lấy data thống kê
            u_data = await data_coll.find_one({"_id": u_id})
            fav_count = len(u_data.get("favorites", [])) if u_data else 0
            pl_count = len(u_data.get("playlists", [])) if u_data else 0
            
            # Tính toán trạng thái Online (trong vòng 90 giây gần nhất)
            last_seen = doc.get("last_seen", 0)
            is_online = False
            last_seen_diff = None
            if last_seen:
                last_seen_diff = int(now - last_seen)
                if last_seen_diff <= 90:
                    is_online = True
                    online_count += 1

            doc["is_online"] = is_online
            doc["last_seen"] = last_seen
            doc["last_seen_diff"] = last_seen_diff
            doc["last_ip"] = doc.get("last_ip", "")
            doc["device_info"] = doc.get("device_info", {})
            doc["current_activity"] = doc.get("current_activity") if is_online else None
            doc["favorites_count"] = fav_count
            doc["playlists_count"] = pl_count
            doc["is_active"] = doc.get("is_active", True)
            users.append(doc)
            
        return JSONResponse(status_code=200, content={
            "status": "success", 
            "users": users,
            "stats": {
                "total": len(users),
                "online": online_count,
                "active": sum(1 for u in users if u.get("is_active") is not False),
                "banned": sum(1 for u in users if u.get("is_active") is False)
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/admin/users")
async def admin_create_music_user(payload: dict, _: bool = Depends(require_auth)):
    """Admin tạo user mới trực tiếp"""
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    display_name = payload.get("display_name", "").strip() or username
    avatar_url = payload.get("avatar_url", "").strip() or f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"
    is_active = payload.get("is_active", True)

    if not username or not password:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Username và Mật khẩu là bắt buộc."})
    
    if len(username) < 3 or len(password) < 6:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Username tối thiểu 3 ký tự, Password tối thiểu 6 ký tự."})

    try:
        coll = db.dbs["tracking"]["music_users"]
        existing = await coll.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        if existing:
            return JSONResponse(status_code=409, content={"status": "error", "message": f"Tài khoản '{username}' đã tồn tại."})

        user_id = f"usr_{secrets.token_hex(8)}"
        user_doc = {
            "_id": user_id,
            "username": username,
            "password_hash": hash_password(password),
            "display_name": display_name,
            "avatar_url": avatar_url,
            "is_active": bool(is_active),
            "created_at": time.time()
        }
        await coll.insert_one(user_doc)
        
        data_coll = db.dbs["tracking"]["music_user_data"]
        await data_coll.insert_one({
            "_id": user_id,
            "favorites": [],
            "playlists": [],
            "history": [],
            "settings": {}
        })

        user_doc.pop("password_hash", None)
        return JSONResponse(status_code=201, content={"status": "success", "message": "Đã tạo người dùng mới thành công.", "user": user_doc})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.put("/api/music/admin/users/{user_id}")
async def admin_update_music_user(user_id: str, payload: dict, _: bool = Depends(require_auth)):
    """Admin cập nhật thông tin user và đổi mật khẩu"""
    display_name = payload.get("display_name")
    avatar_url = payload.get("avatar_url")
    password = payload.get("password")
    is_active = payload.get("is_active")

    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"_id": user_id})
        if not user:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy người dùng."})

        update_fields = {}
        if display_name is not None:
            update_fields["display_name"] = display_name.strip()
        if avatar_url is not None:
            update_fields["avatar_url"] = avatar_url.strip()
        if is_active is not None:
            update_fields["is_active"] = bool(is_active)
        if password:
            if len(password) < 6:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Mật khẩu mới tối thiểu 6 ký tự."})
            update_fields["password_hash"] = hash_password(password)

        if update_fields:
            await coll.update_one({"_id": user_id}, {"$set": update_fields})

        return JSONResponse(status_code=200, content={"status": "success", "message": "Đã cập nhật thông tin người dùng thành công."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/admin/users/{user_id}/toggle-status")
async def admin_toggle_user_status(user_id: str, _: bool = Depends(require_auth)):
    """Admin khóa hoặc mở khóa tài khoản người dùng"""
    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"_id": user_id})
        if not user:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy người dùng."})

        current_status = user.get("is_active", True)
        new_status = not current_status
        await coll.update_one({"_id": user_id}, {"$set": {"is_active": new_status}})

        msg = "Đã mở khóa tài khoản." if new_status else "Đã khóa tài khoản."
        return JSONResponse(status_code=200, content={"status": "success", "message": msg, "is_active": new_status})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.get("/api/music/admin/users/{user_id}/details")
async def admin_get_user_details(user_id: str, _: bool = Depends(require_auth)):
    """Admin lấy chi tiết toàn bộ dữ liệu (Online status, Device, IP, Sessions, Favorites, Playlists, History) của user"""
    try:
        user_coll = db.dbs["tracking"]["music_users"]
        data_coll = db.dbs["tracking"]["music_user_data"]
        now = time.time()

        user = await user_coll.find_one({"_id": user_id})
        if not user:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy người dùng."})

        user.pop("password_hash", None)
        
        # Tính toán trạng thái online
        last_seen = user.get("last_seen", 0)
        is_online = False
        last_seen_diff = None
        if last_seen:
            last_seen_diff = int(now - last_seen)
            if last_seen_diff <= 90:
                is_online = True

        user["is_online"] = is_online
        user["last_seen_diff"] = last_seen_diff

        user_data = await data_coll.find_one({"_id": user_id})
        
        favorites = user_data.get("favorites", []) if user_data else []
        try:
            from Backend.fastapi.routes.music_routes import _db_load_library
            albums = await _db_load_library()
            if albums:
                track_lookup = {}
                for alb in albums:
                    for trk in alb.get("tracks", []):
                        cid = str(trk.get("chat_id") or trk.get("chatId") or "")
                        mid = str(trk.get("msg_id") or trk.get("msgId") or "")
                        if cid and mid:
                            track_lookup[f"{cid}_{mid}"] = trk
                
                for f in favorites:
                    key = f"{f.get('chat_id')}_{f.get('msg_id')}"
                    if key in track_lookup:
                        matched = track_lookup[key]
                        if not f.get("title") and not f.get("name"):
                            f["title"] = matched.get("name") or matched.get("title") or f"Bài #{f.get('msg_id')}"
                        if not f.get("artist"):
                            f["artist"] = matched.get("artist") or ""
                        if not f.get("cover_url"):
                            f["cover_url"] = matched.get("coverUrl") or matched.get("cover_url") or ""
        except Exception:
            pass

        return JSONResponse(status_code=200, content={
            "status": "success",
            "user": user,
            "data": {
                "favorites": favorites,
                "playlists": user_data.get("playlists", []) if user_data else [],
                "history": user_data.get("history", []) if user_data else [],
                "recent_sessions": user.get("recent_sessions", [])
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.delete("/api/music/admin/users/{user_id}")
async def delete_music_user(user_id: str, _: bool = Depends(require_auth)):
    try:
        await db.dbs["tracking"]["music_users"].delete_one({"_id": user_id})
        await db.dbs["tracking"]["music_user_data"].delete_one({"_id": user_id})
        return JSONResponse(status_code=200, content={"status": "success", "message": "Đã xóa user và dữ liệu thành công."})
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
