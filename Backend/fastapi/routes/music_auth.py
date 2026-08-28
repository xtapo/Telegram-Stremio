import time
import secrets
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from Backend import db
from Backend.helper.passwords import hash_password, verify_password

auth_router = APIRouter(tags=["Music Authentication"])

def get_current_music_user(request: Request):
    return request.session.get("music_user_id")

def require_music_auth(request: Request):
    user_id = request.session.get("music_user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để sử dụng tính năng này.")
    return user_id

@auth_router.post("/api/music/auth/register")
async def register_music_user(payload: dict, request: Request):
    username = payload.get("username", "").strip()
    password = payload.get("password", "")
    display_name = payload.get("display_name", "").strip() or username

    if not username or not password:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Username và Password là bắt buộc."})
    
    if len(username) < 3 or len(password) < 6:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Username tối thiểu 3 ký tự, Password tối thiểu 6 ký tự."})

    try:
        coll = db.dbs["tracking"]["music_users"]
        existing = await coll.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})
        if existing:
            return JSONResponse(status_code=409, content={"status": "error", "message": "Username đã tồn tại."})

        user_id = f"usr_{secrets.token_hex(8)}"
        user_doc = {
            "_id": user_id,
            "username": username,
            "password_hash": hash_password(password),
            "display_name": display_name,
            "avatar_url": f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
            "created_at": time.time()
        }
        await coll.insert_one(user_doc)
        
        # Tạo sẵn data rỗng
        data_coll = db.dbs["tracking"]["music_user_data"]
        await data_coll.insert_one({
            "_id": user_id,
            "favorites": [],
            "playlists": [],
            "history": [],
            "settings": {}
        })

        request.session["music_user_id"] = user_id
        request.session["music_username"] = username
        
        return {"status": "success", "message": "Đăng ký thành công!", "user": {"id": user_id, "username": username, "display_name": display_name, "avatar_url": user_doc["avatar_url"]}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


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

        request.session["music_user_id"] = user["_id"]
        request.session["music_username"] = user["username"]
        
        return {"status": "success", "message": "Đăng nhập thành công!", "user": {"id": user["_id"], "username": user["username"], "display_name": user.get("display_name", user["username"]), "avatar_url": user.get("avatar_url", "")}}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@auth_router.post("/api/music/auth/logout")
async def logout_music_user(request: Request):
    request.session.pop("music_user_id", None)
    request.session.pop("music_username", None)
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
            return {"status": "guest", "user": None}
            
        return {
            "status": "authenticated", 
            "user": {
                "id": user["_id"], 
                "username": user["username"], 
                "display_name": user.get("display_name", user["username"]),
                "avatar_url": user.get("avatar_url", "")
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
    if not chat_id or not msg_id:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Thiếu chat_id hoặc msg_id"})
        
    try:
        coll = db.dbs["tracking"]["music_user_data"]
        doc = await coll.find_one({"_id": user_id})
        if not doc:
            await coll.insert_one({"_id": user_id, "favorites": [], "playlists": [], "history": [], "settings": {}})
            doc = {"favorites": []}
            
        favorites = doc.get("favorites", [])
        
        # Check if exists
        target = next((f for f in favorites if str(f.get("chat_id")) == str(chat_id) and str(f.get("msg_id")) == str(msg_id)), None)
        
        is_favorite = False
        if target:
            # Remove
            favorites = [f for f in favorites if not (str(f.get("chat_id")) == str(chat_id) and str(f.get("msg_id")) == str(msg_id))]
        else:
            # Add
            favorites.append({
                "chat_id": int(chat_id),
                "msg_id": int(msg_id),
                "added_at": time.time()
            })
            is_favorite = True
            
        await coll.update_one({"_id": user_id}, {"$set": {"favorites": favorites}})
        return {"status": "success", "is_favorite": is_favorite, "message": "Đã thêm vào yêu thích" if is_favorite else "Đã bỏ yêu thích"}
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
