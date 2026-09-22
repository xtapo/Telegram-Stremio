"""Private, persistent snapshots of music shared with another music account."""

import re
import secrets
import time
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from Backend import db
from Backend.fastapi.routes.music_auth import require_music_auth

router = APIRouter(prefix="/api/music/user/shares", tags=["Music Sharing"])


class FavoriteReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chat_id: str = ""
    msg_id: str = ""
    title: str = Field(default="", max_length=1000)
    artist: str = Field(default="", max_length=1000)


class ShareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient: str = Field(min_length=1, max_length=128)
    kind: Literal["playlist", "favorites"]
    playlist_id: str | None = Field(default=None, max_length=128)
    favorite: FavoriteReference | None = None


class ImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination: Literal["playlist", "favorites"]


def _track_key(track):
    cid = str(track.get("chat_id") or track.get("chatId") or "")
    mid = str(track.get("msg_id") or track.get("msgId") or "")
    if cid and mid:
        return ("telegram", cid, mid)
    return (
        "title",
        str(track.get("name") or track.get("title") or "").strip().casefold(),
        str(track.get("artist") or "").strip().casefold(),
    )


def _safe_url(value):
    value = str(value or "").strip()
    if value.startswith(("https://", "http://")) or (value.startswith("/") and not value.startswith("//")):
        return quote(value, safe="/:?#[]@!$&()*+,;=%")
    return ""


def _snapshot_tracks(tracks):
    result, seen = [], set()
    for track in tracks:
        if not isinstance(track, dict):
            continue
        key = _track_key(track)
        if key in seen:
            continue
        seen.add(key)
        cid = str(track.get("chat_id") or track.get("chatId") or "")
        mid = str(track.get("msg_id") or track.get("msgId") or "")
        preview = _safe_url(track.get("previewUrl") or track.get("url"))
        if cid and mid and cid.lstrip("-").isdigit() and mid.isdigit():
            preview = f"/api/music/stream/{cid}/{mid}"
        if not preview:
            continue
        result.append({
            "id": len(result) + 1,
            "name": str(track.get("name") or track.get("title") or "Bài hát"),
            "artist": str(track.get("artist") or ""),
            "chatId": cid,
            "msgId": mid,
            "previewUrl": preview,
            "coverUrl": _safe_url(track.get("coverUrl") or track.get("cover_url") or track.get("albumCover")),
            "duration": str(track.get("duration") or "--:--"),
            "format": str(track.get("format") or ""),
        })
    return result


async def _received_share(share_id, user_id):
    share = await db.dbs["tracking"]["music_user_shares"].find_one(
        {"_id": share_id, "recipient_id": user_id}
    )
    if not share:
        raise HTTPException(404, "Không tìm thấy nội dung được chia sẻ.")
    return share


def _public_share(share):
    return {"id": share["_id"], **{
        key: share[key] for key in ("title", "kind", "sender_name", "created_at", "track_count", "tracks")
        if key in share
    }}


@router.post("")
async def send_music_share(payload: ShareRequest, user_id: str = Depends(require_music_auth)):
    users = db.dbs["tracking"]["music_users"]
    username = payload.recipient.strip().lstrip("@").strip()
    if not username:
        raise HTTPException(400, "Vui lòng nhập tên đăng nhập của người nhận.")
    recipient = await users.find_one({"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}})
    if not recipient or recipient.get("is_active") is False:
        raise HTTPException(404, "Không tìm thấy tài khoản nhận đang hoạt động.")
    if recipient["_id"] == user_id:
        raise HTTPException(400, "Hãy chọn người dùng khác để chia sẻ.")

    source = await db.dbs["tracking"]["music_user_data"].find_one({"_id": user_id}) or {}
    if payload.kind == "playlist":
        if payload.favorite is not None or not payload.playlist_id:
            raise HTTPException(400, "Vui lòng chọn playlist cần chia sẻ.")
        playlist = next((p for p in source.get("playlists", []) if p.get("id") == payload.playlist_id), None)
        if not playlist:
            raise HTTPException(404, "Không tìm thấy playlist của bạn.")
        title, tracks = playlist.get("name") or "Playlist", playlist.get("tracks", [])
    else:
        if payload.playlist_id is not None:
            raise HTTPException(400, "Thông tin chia sẻ yêu thích không hợp lệ.")
        title, tracks = "Bài hát yêu thích", source.get("favorites", [])
        if payload.favorite is not None:
            key = _track_key(payload.favorite.model_dump())
            tracks = [t for t in tracks if _track_key(t) == key]
            if not tracks:
                raise HTTPException(404, "Bài hát không còn trong danh sách yêu thích của bạn.")
            title = tracks[0].get("title") or tracks[0].get("name") or "Bài hát yêu thích"

    snapshot = _snapshot_tracks(tracks)
    if not snapshot:
        raise HTTPException(400, "Danh sách chưa có bài hát có thể chia sẻ.")
    if len(snapshot) > 2000:
        raise HTTPException(400, "Mỗi lần chia sẻ tối đa 2.000 bài hát. Hãy chia thành playlist nhỏ hơn.")
    sender = await users.find_one({"_id": user_id}) or {}
    share = {
        "_id": secrets.token_hex(16),
        "recipient_id": recipient["_id"],
        "sender_id": user_id,
        "sender_name": sender.get("display_name") or sender.get("username") or "Người dùng",
        "title": title,
        "kind": payload.kind,
        "tracks": snapshot,
        "track_count": len(snapshot),
        "created_at": time.time(),
    }
    await db.dbs["tracking"]["music_user_shares"].insert_one(share)
    return {"status": "success", "message": "Đã chia sẻ với người nhận.", "share_id": share["_id"]}


@router.get("")
async def list_music_shares(offset: int = Query(0, ge=0), user_id: str = Depends(require_music_auth)):
    cursor = db.dbs["tracking"]["music_user_shares"].find(
        {"recipient_id": user_id}, {"tracks": 0}
    ).sort([("created_at", -1), ("_id", -1)]).skip(offset).limit(21)
    shares = await cursor.to_list(length=21)
    return {"status": "success", "shares": [_public_share(s) for s in shares[:20]], "has_more": len(shares) > 20}


@router.get("/{share_id}")
async def get_music_share(share_id: str, user_id: str = Depends(require_music_auth)):
    return {"status": "success", "share": _public_share(await _received_share(share_id, user_id))}


@router.post("/{share_id}/import")
async def import_music_share(share_id: str, payload: ImportRequest, user_id: str = Depends(require_music_auth)):
    share = await _received_share(share_id, user_id)
    coll = db.dbs["tracking"]["music_user_data"]
    await coll.update_one({"_id": user_id}, {"$setOnInsert": {"playlists": [], "favorites": []}}, upsert=True)
    if payload.destination == "playlist":
        # An atomic source marker prevents duplicate imports; copies get their own ID.
        playlist = {
            "id": f"pl_{secrets.token_hex(8)}", "source_share_id": share_id, "name": share["title"],
            "tracks": share["tracks"], "created_at": time.time(),
        }
        result = await coll.update_one(
            {"_id": user_id, "playlists.source_share_id": {"$ne": share_id}},
            {"$push": {"playlists": playlist}},
        )
        return {"status": "success", "message": "Đã lưu thành playlist riêng." if result.modified_count else "Playlist này đã được lưu."}

    # Compare-and-swap preserves favorites added/removed while this import is in flight.
    for _ in range(5):
        doc = await coll.find_one({"_id": user_id}) or {}
        existing = doc.get("favorites", [])
        keys = {_track_key(t) for t in existing}
        additions = []
        for track in share["tracks"]:
            key = _track_key(track)
            if key in keys:
                continue
            keys.add(key)
            additions.append({
                **track, "chat_id": track["chatId"], "msg_id": track["msgId"],
                "title": track["name"], "cover_url": track["coverUrl"], "added_at": time.time(),
            })
        if not additions:
            return {"status": "success", "message": "Các bài hát đã có trong danh sách yêu thích.", "added_count": 0}
        result = await coll.update_one(
            {"_id": user_id, "favorites": existing if "favorites" in doc else {"$exists": False}},
            {"$set": {"favorites": existing + additions}},
        )
        if result.modified_count:
            return {"status": "success", "message": f"Đã thêm {len(additions)} bài vào yêu thích.", "added_count": len(additions)}
    raise HTTPException(409, "Danh sách yêu thích vừa thay đổi. Vui lòng thử lại.")


@router.delete("/{share_id}")
async def dismiss_music_share(share_id: str, user_id: str = Depends(require_music_auth)):
    result = await db.dbs["tracking"]["music_user_shares"].delete_one({"_id": share_id, "recipient_id": user_id})
    if not result.deleted_count:
        raise HTTPException(404, "Không tìm thấy nội dung được chia sẻ.")
    return {"status": "success", "message": "Đã bỏ khỏi mục được chia sẻ."}
