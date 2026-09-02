import re
import time
import secrets
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, HTMLResponse, Response as PlainResponse
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
    
    # Kiểm tra xem user có được duyệt / hoạt động không
    coll = db.dbs["tracking"]["music_users"]
    user = await coll.find_one({"_id": user_id})
    if not user or user.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Tài khoản của bạn đang chờ Quản trị viên phê duyệt hoặc đã bị tạm khóa.")
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
        user_doc = await coll.find_one({"_id": user_id})
        
        device_str = f"{device_details['os']} • {device_details['browser']}"
        existing_sessions = (user_doc.get("recent_sessions", []) if user_doc else [])
        
        should_add_new_session = False
        if not existing_sessions:
            should_add_new_session = True
        else:
            last_sess = existing_sessions[-1]
            # Nếu khác IP, hoặc khác Thiết bị/Trình duyệt, hoặc cách lần trước > 6 tiếng (21600 giây)
            if last_sess.get("ip") != client_ip or last_sess.get("device") != device_str or (now - last_sess.get("last_active", 0)) > 21600:
                should_add_new_session = True

        update_fields = {
            "last_seen": now,
            "last_ip": client_ip,
            "device_info": device_details,
            "current_activity": current_activity
        }

        if should_add_new_session:
            session_entry = {
                "ip": client_ip,
                "device": device_str,
                "device_type": device_details["device_type"],
                "last_active": now
            }
            await coll.update_one(
                {"_id": user_id},
                {
                    "$set": update_fields,
                    "$push": {
                        "recent_sessions": {
                            "$each": [session_entry],
                            "$slice": -10  # Giữ lại tối đa 10 phiên gần nhất
                        }
                    }
                }
            )
        else:
            # Cập nhật thời gian hoạt động của phiên gần nhất nếu cần mà không tạo dòng mới
            existing_sessions[-1]["last_active"] = now
            update_fields["recent_sessions"] = existing_sessions[-10:]
            await coll.update_one(
                {"_id": user_id},
                {"$set": update_fields}
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
        if not user:
            request.session.pop("music_user_id", None)
            request.session.pop("music_username", None)
            return {"status": "guest", "user": None}

        if user.get("is_active") is False:
            return {
                "status": "pending_approval",
                "message": "Tài khoản Telegram của bạn đang chờ Quản trị viên phê duyệt quyền sử dụng.",
                "user": {
                    "id": user["_id"],
                    "username": user["username"],
                    "display_name": user.get("display_name", user["username"]),
                    "avatar_url": user.get("avatar_url", ""),
                    "is_active": False,
                    "is_channel_member": user.get("is_channel_member", True),
                    "channel_warning": user.get("channel_warning"),
                    "auth_type": user.get("auth_type", "password")
                }
            }
            
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

def _dedup_tracks(tracks: list) -> list:
    if not tracks or not isinstance(tracks, list):
        return []
    seen = set()
    deduped = []
    for t in tracks:
        if not isinstance(t, dict):
            continue
        cid = str(t.get("chat_id") or t.get("chatId") or "")
        mid = str(t.get("msg_id") or t.get("msgId") or "")
        name = (t.get("name") or t.get("title") or "").strip().lower()
        artist = (t.get("artist") or "").strip().lower()
        key = f"{cid}_{mid}" if (cid and mid) else f"{name}_{artist}"
        if key and key not in seen:
            seen.add(key)
            deduped.append(t)
    return deduped

def _dedup_favorites(favs: list) -> list:
    if not favs or not isinstance(favs, list):
        return []
    seen = set()
    deduped = []
    for f in favs:
        if not isinstance(f, dict):
            continue
        cid = str(f.get("chat_id") or f.get("chatId") or "")
        mid = str(f.get("msg_id") or f.get("msgId") or "")
        title = (f.get("title") or f.get("name") or "").strip().lower()
        artist = (f.get("artist") or "").strip().lower()
        key = f"{cid}_{mid}" if (cid and mid) else f"{title}_{artist}"
        if key and key not in seen:
            seen.add(key)
            deduped.append(f)
    return deduped

@auth_router.get("/api/music/user/favorites")
async def get_user_favorites(user_id: str = Depends(require_music_auth)):
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        raw_favs = doc.get("favorites", []) if doc else []
        favorites = _dedup_favorites(raw_favs)
        if len(favorites) != len(raw_favs) and doc:
            await coll.update_one({"_id": user_id}, {"$set": {"favorites": favorites}})
        return {"status": "success", "favorites": favorites}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.post("/api/music/user/favorites/toggle")
async def toggle_user_favorite(payload: dict, user_id: str = Depends(require_music_auth)):
    chat_id = payload.get("chat_id")
    msg_id = payload.get("msg_id")
    track_name = (payload.get("name") or payload.get("title") or "").strip()
    
    if chat_id is None and msg_id is None and not track_name:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu thông tin bài hát"})
        
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        if not doc:
            await coll.insert_one({"_id": user_id, "favorites": [], "playlists": [], "history": [], "settings": {}})
            doc = {"favorites": []}
            
        favorites = _dedup_favorites(doc.get("favorites", []))
        
        # Check if already in favorites
        def matches(f):
            fcid = str(f.get("chat_id") or f.get("chatId") or "")
            fmid = str(f.get("msg_id") or f.get("msgId") or "")
            ftitle = (f.get("title") or f.get("name") or "").strip().lower()
            if chat_id is not None and msg_id is not None and fcid == str(chat_id) and fmid == str(msg_id):
                return True
            if msg_id is not None and fmid == str(msg_id) and fmid:
                return True
            if track_name and ftitle == track_name.lower():
                return True
            return False

        target = next((f for f in favorites if matches(f)), None)
        
        is_favorite = False
        if target:
            favorites = [f for f in favorites if not matches(f)]
        else:
            cid = int(chat_id) if str(chat_id).lstrip('-').isdigit() else str(chat_id) if chat_id else ""
            mid = int(msg_id) if str(msg_id).lstrip('-').isdigit() else str(msg_id) if msg_id else ""
            artist = payload.get("artist") or ""
            cover_url = payload.get("cover_url") or payload.get("coverUrl") or ""
            favorites.append({
                "chat_id": cid,
                "msg_id": mid,
                "title": track_name or (f"Bài #{mid}" if mid else "Bài hát"),
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
        
        # Auto-dedup tracks inside each playlist
        changed = False
        for p in playlists:
            raw_tr = p.get("tracks", [])
            deduped_tr = _dedup_tracks(raw_tr)
            if len(deduped_tr) != len(raw_tr):
                p["tracks"] = deduped_tr
                changed = True
        if changed and doc:
            await coll.update_one({"_id": user_id}, {"$set": {"playlists": playlists}})
            
        return {"status": "success", "playlists": playlists}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@auth_router.post("/api/music/user/playlists")
async def create_user_playlist(payload: dict, user_id: str = Depends(require_music_auth)):
    name = payload.get("name", "").strip()
    raw_tracks = payload.get("tracks", [])
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
            "tracks": _dedup_tracks(raw_tracks),
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
            target["tracks"] = _dedup_tracks(tracks)
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
                "active": sum(1 for u in users if u.get("is_active") is True),
                "pending": sum(1 for u in users if u.get("is_active") is False),
                "banned": sum(1 for u in users if u.get("is_active") is False)
            }
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/admin/users/{user_id}/approve")
async def admin_approve_music_user(user_id: str, _: bool = Depends(require_auth)):
    """Admin phê duyệt tài khoản người dùng"""
    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"_id": user_id})
        if not user:
            return JSONResponse(status_code=404, content={"status": "error", "message": "Không tìm thấy người dùng."})

        await coll.update_one(
            {"_id": user_id},
            {"$set": {"is_active": True, "approved_at": time.time()}}
        )

        display_name = user.get("display_name") or user.get("username")
        return JSONResponse(
            status_code=200, 
            content={"status": "success", "message": f"Đã phê duyệt tài khoản '{display_name}' thành công!", "is_active": True}
        )
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

        # Lọc và gộp các phiên trùng lặp liên tiếp
        raw_sessions = user.get("recent_sessions", [])
        dedup_sessions = []
        for s in raw_sessions:
            if not dedup_sessions:
                dedup_sessions.append(s)
            else:
                prev = dedup_sessions[-1]
                if prev.get("ip") == s.get("ip") and prev.get("device") == s.get("device") and abs(s.get("last_active", 0) - prev.get("last_active", 0)) < 21600:
                    prev["last_active"] = max(prev.get("last_active", 0), s.get("last_active", 0))
                else:
                    dedup_sessions.append(s)

        # Cập nhật lại danh sách đã làm sạch vào database nếu có sự khác biệt
        if len(dedup_sessions) != len(raw_sessions):
            await user_coll.update_one({"_id": user_id}, {"$set": {"recent_sessions": dedup_sessions}})

        return JSONResponse(status_code=200, content={
            "status": "success",
            "user": user,
            "data": {
                "favorites": favorites,
                "playlists": user_data.get("playlists", []) if user_data else [],
                "history": user_data.get("history", []) if user_data else [],
                "recent_sessions": dedup_sessions
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


# ─────────────────────────────────────────────────────────────────────────────
# 📺 TV QR LOGIN & PHONE-TO-TV AUTHENTICATION TRANSFER
# ─────────────────────────────────────────────────────────────────────────────
_TV_QR_SESSIONS: dict = {}


@auth_router.post("/api/music/auth/tv/qr-init")
async def init_tv_qr_session(request: Request):
    """Khởi tạo phiên đăng nhập QR dành cho Android TV / Smart TV"""
    token = f"tv_{secrets.token_urlsafe(20)}"
    base_url = str(request.base_url).rstrip("/")
    transfer_url = f"{base_url}/music/transfer?token={token}"
    
    _TV_QR_SESSIONS[token] = {
        "created_at": time.time(),
        "status": "pending",
        "user_id": None,
        "username": None,
        "user": None
    }
    
    # Dọn dẹp các phiên QR cũ quá 10 phút
    now = time.time()
    for old_tok in list(_TV_QR_SESSIONS.keys()):
        if now - _TV_QR_SESSIONS[old_tok].get("created_at", 0) > 600:
            _TV_QR_SESSIONS.pop(old_tok, None)

    import urllib.parse
    qr_img_url = f"https://api.qrserver.com/v1/create-qr-code/?size=350x350&margin=12&data={urllib.parse.quote(transfer_url)}"

    return {
        "status": "success",
        "token": token,
        "transfer_url": transfer_url,
        "qr_url": qr_img_url,
        "expires_in": 300
    }


@auth_router.get("/api/music/auth/tv/qr-status")
async def check_tv_qr_status(token: str, request: Request):
    """Kiểm tra trạng thái quét mã QR từ phía TV (Polling)"""
    if not token or token not in _TV_QR_SESSIONS:
        return {"status": "expired", "message": "Phiên QR không tồn tại hoặc đã hết hạn"}

    sess = _TV_QR_SESSIONS[token]
    if time.time() - sess.get("created_at", 0) > 300:
        _TV_QR_SESSIONS.pop(token, None)
        return {"status": "expired", "message": "Mã QR đã hết hạn, vui lòng tạo mã mới"}

    if sess.get("status") == "confirmed":
        user_id = sess.get("user_id")
        username = sess.get("username")
        user_data = sess.get("user")
        
        # Gán phiên đăng nhập trực tiếp cho TV
        request.session["music_user_id"] = user_id
        request.session["music_username"] = username
        _TV_QR_SESSIONS.pop(token, None)

        return {
            "status": "confirmed",
            "message": "Đăng nhập TV thành công!",
            "user": user_data
        }

    return {"status": "pending", "message": "Đang chờ quét từ điện thoại..."}


@auth_router.post("/api/music/auth/tv/confirm-transfer")
async def confirm_tv_qr_transfer(payload: dict, request: Request):
    """Xác nhận chuyển trạng thái đăng nhập từ điện thoại sang TV"""
    token = payload.get("token")
    if not token or token not in _TV_QR_SESSIONS:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Mã phiên TV không hợp lệ hoặc đã hết hạn."})

    user_id = request.session.get("music_user_id")
    if not user_id:
        return JSONResponse(status_code=401, content={"status": "unauthorized", "message": "Bạn chưa đăng nhập trên điện thoại."})

    try:
        coll = db.dbs["tracking"]["music_users"]
        user = await coll.find_one({"_id": user_id})
        if not user or user.get("is_active") is False:
            return JSONResponse(status_code=403, content={"status": "error", "message": "Tài khoản không hợp lệ hoặc đã bị khóa."})

        user_info = {
            "id": user["_id"],
            "username": user["username"],
            "display_name": user.get("display_name", user["username"]),
            "avatar_url": user.get("avatar_url", ""),
            "is_active": user.get("is_active", True)
        }

        _TV_QR_SESSIONS[token]["status"] = "confirmed"
        _TV_QR_SESSIONS[token]["user_id"] = user["_id"]
        _TV_QR_SESSIONS[token]["username"] = user["username"]
        _TV_QR_SESSIONS[token]["user"] = user_info

        return {
            "status": "success",
            "message": "Đã cho phép TV đăng nhập thành công!",
            "user": user_info
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.get("/music/transfer", response_class=HTMLResponse)
@auth_router.get("/music/auth/transfer", response_class=HTMLResponse)
async def tv_transfer_page(token: str = "", request: Request = None):
    """Trang giao diện xác nhận chuyển đăng nhập sang TV khi quét QR trên điện thoại"""
    from fastapi.responses import HTMLResponse
    user_id = request.session.get("music_user_id")
    username = request.session.get("music_username") or "Người dùng"
    display_name = username
    avatar_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}"

    if user_id:
        try:
            coll = db.dbs["tracking"]["music_users"]
            u = await coll.find_one({"_id": user_id})
            if u:
                display_name = u.get("display_name") or u.get("username")
                if u.get("avatar_url"):
                    avatar_url = u.get("avatar_url")
        except Exception:
            pass

    is_logged_in = bool(user_id)

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Xác Nhận Đăng Nhập TV - XTAPO MUSIC</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: #0b0e14;
            color: #f1f5f9;
            font-family: system-ui, -apple-system, Roboto, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: #141923;
            border: 2px solid #232a38;
            border-radius: 20px;
            padding: 32px 24px;
            max-width: 420px;
            width: 100%;
            text-align: center;
            box-shadow: 0 12px 40px rgba(0,0,0,0.6);
        }}
        .logo-icon {{
            width: 64px;
            height: 64px;
            background: rgba(245, 158, 11, 0.15);
            border: 2px solid #f59e0b;
            border-radius: 50%;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #f59e0b;
            font-size: 28px;
            margin-bottom: 16px;
        }}
        h2 {{ font-size: 22px; font-weight: 800; color: #f8fafc; margin-bottom: 8px; }}
        p {{ font-size: 15px; color: #94a3b8; line-height: 1.5; margin-bottom: 24px; }}
        .user-box {{
            background: #1a2230;
            border: 1px solid #334155;
            border-radius: 14px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 24px;
            text-align: left;
        }}
        .avatar {{
            width: 48px;
            height: 48px;
            border-radius: 50%;
            object-fit: cover;
            border: 2px solid #f59e0b;
        }}
        .user-name {{ font-size: 16px; font-weight: 700; color: #f8fafc; }}
        .user-sub {{ font-size: 13px; color: #38bdf8; }}
        .btn {{
            width: 100%;
            padding: 14px;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 800;
            cursor: pointer;
            border: none;
            outline: none;
            transition: all 0.2s;
        }}
        .btn-confirm {{
            background: linear-gradient(135deg, #f59e0b, #d97706);
            color: #0b0e14;
            box-shadow: 0 4px 16px rgba(245, 158, 11, 0.4);
            margin-bottom: 12px;
        }}
        .btn-confirm:active {{ transform: scale(0.98); }}
        .btn-cancel {{
            background: #1e2532;
            color: #94a3b8;
            border: 1px solid #334155;
        }}
        .status-box {{
            display: none;
            padding: 16px;
            border-radius: 12px;
            font-size: 15px;
            font-weight: 700;
            margin-top: 16px;
        }}
        .status-success {{ background: rgba(34, 197, 94, 0.2); color: #4ade80; border: 1px solid #22c55e; }}
        .status-error {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
        .login-form {{ text-align: left; margin-bottom: 20px; }}
        .input-group {{ margin-bottom: 14px; }}
        .input-label {{ font-size: 13px; font-weight: 700; color: #94a3b8; margin-bottom: 6px; display: block; }}
        .input-field {{
            width: 100%;
            padding: 12px 14px;
            background: #1a2230;
            border: 1px solid #334155;
            border-radius: 10px;
            color: #fff;
            font-size: 15px;
            outline: none;
        }}
        .input-field:focus {{ border-color: #f59e0b; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo-icon">📺</div>
        <h2>Đăng Nhập Android TV</h2>
        <p>Cho phép thiết bị Android TV / Smart TV kết nối và phát nhạc từ tài khoản của bạn.</p>

        {"<!-- User Box If Logged In -->" if is_logged_in else ""}
        {f'''
        <div class="user-box" id="userBox">
            <img src="{avatar_url}" class="avatar" alt="">
            <div>
                <div class="user-name">{display_name}</div>
                <div class="user-sub">@{username} (Đã đăng nhập)</div>
            </div>
        </div>
        <button class="btn btn-confirm" id="btnConfirm">✅ Xác Nhận Đăng Nhập Trên TV</button>
        <button class="btn btn-cancel" onclick="window.close()">Hủy Bỏ</button>
        ''' if is_logged_in else f'''
        <div class="login-form">
            <div class="input-group">
                <label class="input-label">Tài khoản</label>
                <input type="text" class="input-field" id="txtUsername" placeholder="Nhập username...">
            </div>
            <div class="input-group">
                <label class="input-label">Mật khẩu</label>
                <input type="password" class="input-field" id="txtPassword" placeholder="Nhập mật khẩu...">
            </div>
            <button class="btn btn-confirm" id="btnLoginAndConfirm">🔐 Đăng Nhập & Chuyển Sang TV</button>
        </div>
        '''}

        <div class="status-box" id="statusBox"></div>
    </div>

    <script>
        const token = "{token}";
        const statusBox = document.getElementById('statusBox');

        function showStatus(msg, isSuccess) {{
            statusBox.style.display = 'block';
            statusBox.className = 'status-box ' + (isSuccess ? 'status-success' : 'status-error');
            statusBox.textContent = msg;
        }}

        const btnConfirm = document.getElementById('btnConfirm');
        if (btnConfirm) {{
            btnConfirm.addEventListener('click', async () => {{
                btnConfirm.disabled = true;
                btnConfirm.textContent = 'Đang xử lý...';
                try {{
                    const res = await fetch('/api/music/auth/tv/confirm-transfer', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ token: token }})
                    }});
                    const data = await res.json();
                    if (res.ok && data.status === 'success') {{
                        showStatus('🎉 ' + data.message, true);
                        btnConfirm.style.display = 'none';
                        setTimeout(() => {{
                            window.location.href = '/music';
                        }}, 2000);
                    }} else {{
                        showStatus(data.message || 'Xác nhận thất bại', false);
                        btnConfirm.disabled = false;
                        btnConfirm.textContent = 'Thử lại';
                    }}
                }} catch (e) {{
                    showStatus('Lỗi kết nối máy chủ: ' + e.message, false);
                    btnConfirm.disabled = false;
                }}
            }});
        }}

        const btnLogin = document.getElementById('btnLoginAndConfirm');
        if (btnLogin) {{
            btnLogin.addEventListener('click', async () => {{
                const u = document.getElementById('txtUsername').value.trim();
                const p = document.getElementById('txtPassword').value;
                if (!u || !p) {{
                    showStatus('Vui lòng nhập đầy đủ tài khoản và mật khẩu', false);
                    return;
                }}
                btnLogin.disabled = true;
                btnLogin.textContent = 'Đang đăng nhập...';
                try {{
                    const resLogin = await fetch('/api/music/auth/login', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ username: u, password: p }})
                    }});
                    const loginData = await resLogin.json();
                    if (!resLogin.ok || loginData.status !== 'success') {{
                        showStatus(loginData.message || 'Đăng nhập thất bại', false);
                        btnLogin.disabled = false;
                        btnLogin.textContent = '🔐 Đăng Nhập & Chuyển Sang TV';
                        return;
                    }}

                    // Chuyển luôn sang TV
                    const resConfirm = await fetch('/api/music/auth/tv/confirm-transfer', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ token: token }})
                    }});
                    const confirmData = await resConfirm.json();
                    if (resConfirm.ok && confirmData.status === 'success') {{
                        showStatus('🎉 Đăng nhập & chuyển sang TV thành công!', true);
                        setTimeout(() => {{ window.location.href = '/music'; }}, 2000);
                    }} else {{
                        showStatus(confirmData.message || 'Không thể chuyển sang TV', false);
                    }}
                }} catch (e) {{
                    showStatus('Lỗi kết nối: ' + e.message, false);
                    btnLogin.disabled = false;
                }}
            }});
        }}
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)
