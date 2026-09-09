import asyncio
import gzip
import hashlib
import json
import math
import mimetypes
import os
import re
import secrets
import shutil
import subprocess
import time
import unicodedata
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote, unquote
import httpx

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.responses import Response as PlainResponse
from fastapi.responses import StreamingResponse

from Backend import db
from pyrogram.errors import AuthBytesInvalid, FloodWait
from Backend.helper.custom_dl import ByteStreamer, get_client_dc_lock
from Backend.helper.music_cache import (
    BLOCK_SIZE as AUDIO_CACHE_BLOCK_SIZE,
    PLAYBACK_WINDOW_TTL,
    smart_audio_cache,
)
from Backend.helper.metadata.music_pipeline import (
    metadata_confidence,
    music_metadata_pipeline,
    normalize_metadata_source,
)
from Backend.logger import LOGGER
import Backend.pyrofork.bot as botmod
from Backend.pyrofork.bot import StreamBot, Userbot, USERBOT_CLIENT_INDEX, multi_clients, work_loads, client_dc_map, client_failures
from Backend.fastapi.routes.stream_routes import select_best_client, _get_streamer, parse_range_header, _resolve_filename_mime, _build_stream_headers, get_parallel_prefetch
from Backend.fastapi.security.credentials import get_current_user, require_auth
from Backend.fastapi.routes.template_routes import _base_context, templates

router = APIRouter(tags=["Music Player & Telegram Storage"])

# ==============================================================================
# REAL-TIME SYNCED LYRICS (LRCLIB & CUSTOM LRC ENGINE)
# ==============================================================================

_lyrics_memory_cache: Dict[str, dict] = {}
_LYRICS_CACHE_TTL = 86400 * 7  # 7 days

def _split_artist_title(raw_text: str):
    """Tách Tên Ca Sĩ - Tên Bài Hát từ chuỗi tổng hợp (vd: Sơn Tùng - Chúng Ta Của Hiện Tại)"""
    if not raw_text:
        return "", ""
    t = raw_text.strip()
    t = re.sub(r'^\s*\d+[\s\.\-_]+', '', t)
    t = re.sub(r'\.(flac|mp3|m4a|wav|aac|ogg)$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)', '', t, flags=re.IGNORECASE)
    
    # Thử tách theo " - " hoặc " – " hoặc " — "
    for sep in (' - ', ' – ', ' — ', ' // '):
        if sep in t:
            parts = t.split(sep, 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            if p1 and p2:
                return p1, p2
    return "", t.strip()

def _clean_track_title_for_lyrics(title: str) -> str:
    """Làm sạch tên bài hát để tăng tỷ lệ tìm kiếm chính xác trên LRCLIB"""
    if not title:
        return ""
    p_artist, p_title = _split_artist_title(title)
    t = p_title if p_title else title
    t = re.sub(r'^\s*\d+[\s\.\-_]+', '', t)
    t = re.sub(r'\.(flac|mp3|m4a|wav|aac|ogg)$', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\[.*?\]', '', t)
    t = re.sub(r'\((?:official|music|video|audio|lyrics|remaster|remastered|version|deluxe|bonus|expanded|edition|karaoke|beat|instrumental|hd|4k|live).*?\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def _clean_artist_name_for_lyrics(artist: str, raw_title: str = "") -> str:
    if artist and artist.lower() not in ("unknown", "various artists", "xtapo music", "chưa rõ", "none"):
        a = re.sub(r'\[.*?\]', '', artist)
        a = re.sub(r'\s+', ' ', a).strip()
        return a
    # Thử lấy artist từ raw_title nếu raw_title có dạng "Artist - Title"
    p_artist, _ = _split_artist_title(raw_title)
    if p_artist and p_artist.lower() not in ("unknown", "various artists", "xtapo music", "chưa rõ", "none"):
        return p_artist
    return ""

@router.get("/api/music/lyrics")
async def get_realtime_lyrics(
    track_name: str = Query(..., description="Tên bài hát"),
    artist_name: Optional[str] = Query(None, description="Tên ca sĩ / nghệ sĩ"),
    album_name: Optional[str] = Query(None, description="Tên album"),
    duration: Optional[str] = Query(None, description="Thời lượng tính bằng giây"),
    force_refresh: Optional[bool] = Query(False, description="Bỏ qua cache")
):
    """
    Lấy lời bài hát đồng bộ từng giây (Synced Lyrics .LRC) từ LRCLIB.
    Tự động thử nhiều chiến lược: Exact Match -> Search Cleaned Title -> Fuzzy Search.
    """
    parsed_duration: Optional[float] = None
    if duration:
        try:
            val = float(str(duration).strip())
            if val > 0:
                parsed_duration = val
        except (ValueError, TypeError):
            parsed_duration = None
    duration = parsed_duration
    cleaned_track = _clean_track_title_for_lyrics(track_name)
    cleaned_artist = _clean_artist_name_for_lyrics(artist_name or "", track_name)
    
    cache_key = f"{cleaned_track.lower()}__{cleaned_artist.lower()}"
    
    # 1. Kiểm tra cache RAM
    if not force_refresh and cache_key in _lyrics_memory_cache:
        cached_entry = _lyrics_memory_cache[cache_key]
        if time.time() - cached_entry.get("_cached_at", 0) < _LYRICS_CACHE_TTL:
            return JSONResponse(content=cached_entry["data"])
    
    # 2. Kiểm tra Database MongoDB nếu đã lưu tùy chỉnh
    if db is not None and not force_refresh:
        try:
            coll = db.get_collection("music_custom_lyrics")
            if coll is not None:
                doc = await coll.find_one({"_id": cache_key})
                if doc:
                    doc_data = {
                        "status": "success",
                        "id": doc.get("id", 0),
                        "track_name": doc.get("track_name", cleaned_track),
                        "artist_name": doc.get("artist_name", cleaned_artist),
                        "synced_lyrics": doc.get("synced_lyrics", ""),
                        "plain_lyrics": doc.get("plain_lyrics", ""),
                        "instrumental": doc.get("instrumental", False),
                        "is_custom": True,
                        "source": "custom_db"
                    }
                    _lyrics_memory_cache[cache_key] = {"data": doc_data, "_cached_at": time.time()}
                    return JSONResponse(content=doc_data)
        except Exception as e:
            LOGGER.debug(f"[Lyrics DB Check] Note: {e}")

    headers = {
        "User-Agent": "XTAPO-Music-Player/2.0 (https://github.com/xtapo/Telegram-Stremio)"
    }
    
    async with httpx.AsyncClient(timeout=9.0, follow_redirects=True) as client:
        # A1: Thử /api/get exact match (with duration)
        if duration and duration > 0:
            try:
                get_params = {"track_name": cleaned_track, "duration": int(duration)}
                if cleaned_artist: get_params["artist_name"] = cleaned_artist
                if album_name and album_name.strip(): get_params["album_name"] = album_name.strip()
                resp = await client.get("https://lrclib.net/api/get", params=get_params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("syncedLyrics"):
                        result = {
                            "status": "success",
                            "id": data.get("id"),
                            "track_name": data.get("trackName") or cleaned_track,
                            "artist_name": data.get("artistName") or cleaned_artist,
                            "album_name": data.get("albumName") or album_name,
                            "duration": data.get("duration"),
                            "synced_lyrics": data.get("syncedLyrics") or "",
                            "plain_lyrics": data.get("plainLyrics") or "",
                            "instrumental": data.get("instrumental", False),
                            "source": "lrclib_exact"
                        }
                        _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                        return JSONResponse(content=result)
            except Exception as e:
                LOGGER.debug(f"[LRCLIB Exact Duration] Note: {e}")

        # A2: Thử /api/get exact match (without duration)
        try:
            get_params = {"track_name": cleaned_track}
            if cleaned_artist: get_params["artist_name"] = cleaned_artist
            if album_name and album_name.strip(): get_params["album_name"] = album_name.strip()
            resp = await client.get("https://lrclib.net/api/get", params=get_params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("syncedLyrics") or data.get("plainLyrics"):
                    result = {
                        "status": "success",
                        "id": data.get("id"),
                        "track_name": data.get("trackName") or cleaned_track,
                        "artist_name": data.get("artistName") or cleaned_artist,
                        "album_name": data.get("albumName") or album_name,
                        "duration": data.get("duration"),
                        "synced_lyrics": data.get("syncedLyrics") or "",
                        "plain_lyrics": data.get("plainLyrics") or "",
                        "instrumental": data.get("instrumental", False),
                        "source": "lrclib_exact_nodur"
                    }
                    _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                    return JSONResponse(content=result)
        except Exception as e:
            LOGGER.debug(f"[LRCLIB Exact NoDur] Note: {e}")

        # B: Thu thập kết quả từ nhiều truy vấn tìm kiếm
        search_queries = []
        if cleaned_artist:
            search_queries.append(f"{cleaned_track} {cleaned_artist}")
            search_queries.append(f"{cleaned_artist} {cleaned_track}")
        search_queries.append(cleaned_track)

        collected_items = []
        for q_str in search_queries:
            try:
                resp = await client.get("https://lrclib.net/api/search", params={"q": q_str}, headers=headers)
                if resp.status_code == 200:
                    items = resp.json()
                    if isinstance(items, list) and len(items) > 0:
                        collected_items.extend(items)
                        # Nếu đã có ít nhất 1 item có syncedLyrics, không cần search thêm
                        if any(it.get("syncedLyrics") for it in items):
                            break
            except Exception as e:
                LOGGER.debug(f"[LRCLIB Search '{q_str}'] Note: {e}")

        if collected_items:
            # Chấm điểm và xếp hạng kết quả tốt nhất
            def score_item(item):
                s = 0
                has_synced = bool(item.get("syncedLyrics"))
                if has_synced:
                    s += 1000  # Ưu tiên tuyệt đối lời có đồng bộ
                
                # Khớp tên bài hát
                i_name = (item.get("trackName") or "").lower()
                if i_name == cleaned_track.lower():
                    s += 300
                elif cleaned_track.lower() in i_name or i_name in cleaned_track.lower():
                    s += 150
                
                # Khớp tên ca sĩ
                if cleaned_artist:
                    i_art = (item.get("artistName") or "").lower()
                    if i_art == cleaned_artist.lower():
                        s += 250
                    elif cleaned_artist.lower() in i_art or i_art in cleaned_artist.lower():
                        s += 100
                
                # Khớp thời lượng (gần nhất)
                if duration and duration > 0 and item.get("duration"):
                    diff = abs(item["duration"] - duration)
                    if diff <= 3:
                        s += 200
                    elif diff <= 8:
                        s += 100
                    elif diff <= 20:
                        s += 40
                    else:
                        s -= min(100, int(diff * 2))
                return s

            collected_items.sort(key=score_item, reverse=True)
            best_match = collected_items[0]

            synced = best_match.get("syncedLyrics") or ""
            plain = best_match.get("plainLyrics") or ""

            if synced:
                result = {
                    "status": "success",
                    "id": best_match.get("id"),
                    "track_name": best_match.get("trackName") or cleaned_track,
                    "artist_name": best_match.get("artistName") or cleaned_artist,
                    "album_name": best_match.get("albumName") or album_name,
                    "duration": best_match.get("duration"),
                    "synced_lyrics": synced,
                    "plain_lyrics": plain,
                    "instrumental": best_match.get("instrumental", False),
                    "source": "lrclib_ranked_search"
                }
                _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
                return JSONResponse(content=result)

        # 4. Chiến lược D: Thử Netease Cloud Music (163 Music - Siêu mạnh về V-Pop, K-Pop, C-Pop & Quốc Tế)
        try:
            netease_query = f"{cleaned_track} {cleaned_artist}".strip()
            netease_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Referer": "https://music.163.com/"
            }
            n_resp = await client.post(
                "https://music.163.com/api/cloudsearch/pc",
                data={"s": netease_query, "type": 1, "limit": 4},
                headers=netease_headers
            )
            if n_resp.status_code == 200:
                n_data = n_resp.json()
                n_songs = n_data.get("result", {}).get("songs", [])
                for song in n_songs:
                    sid = song.get("id")
                    if not sid:
                        continue
                    r_lrc = await client.get(
                        "https://music.163.com/api/song/lyric",
                        params={"os": "pc", "id": sid, "lv": -1, "kv": -1, "tv": -1},
                        headers=netease_headers
                    )
                    if r_lrc.status_code == 200:
                        l_json = r_lrc.json()
                        raw_lrc = l_json.get("lrc", {}).get("lyric", "").strip()
                        if raw_lrc:
                            has_synced = bool(re.search(r'\[\d{1,2}:\d{1,2}', raw_lrc))
                            artist_str = ""
                            if song.get("ar") and isinstance(song["ar"], list) and len(song["ar"]) > 0:
                                artist_str = song["ar"][0].get("name", "")
                            
                            netease_result = {
                                "status": "success",
                                "id": sid,
                                "track_name": song.get("name") or cleaned_track,
                                "artist_name": artist_str or cleaned_artist,
                                "album_name": (song.get("al") or {}).get("name") or album_name,
                                "duration": int(song.get("dt", 0) / 1000) if song.get("dt") else None,
                                "synced_lyrics": raw_lrc if has_synced else "",
                                "plain_lyrics": "" if has_synced else raw_lrc,
                                "instrumental": False,
                                "source": "netease_cloud"
                            }
                            _lyrics_memory_cache[cache_key] = {"data": netease_result, "_cached_at": time.time()}
                            return JSONResponse(content=netease_result)
        except Exception as e:
            LOGGER.debug(f"[Netease Lyrics Engine] Note: {e}")

        # 5. Nếu chỉ có plain lyrics từ LRCLIB
        if collected_items and collected_items[0].get("plainLyrics"):
            best_p = collected_items[0]
            result = {
                "status": "success",
                "id": best_p.get("id"),
                "track_name": best_p.get("trackName") or cleaned_track,
                "artist_name": best_p.get("artistName") or cleaned_artist,
                "album_name": best_p.get("albumName") or album_name,
                "duration": best_p.get("duration"),
                "synced_lyrics": "",
                "plain_lyrics": best_p.get("plainLyrics") or "",
                "instrumental": best_p.get("instrumental", False),
                "source": "lrclib_plain"
            }
            _lyrics_memory_cache[cache_key] = {"data": result, "_cached_at": time.time()}
            return JSONResponse(content=result)

    # Không tìm thấy lời bài hát
    not_found_res = {
        "status": "not_found",
        "track_name": cleaned_track,
        "artist_name": cleaned_artist,
        "synced_lyrics": "",
        "plain_lyrics": "",
        "message": f"Chưa có sẵn lời bài hát cho '{cleaned_track}'. Bạn có thể dán file .lrc thủ công!"
    }
    _lyrics_memory_cache[cache_key] = {"data": not_found_res, "_cached_at": time.time()}
    return JSONResponse(status_code=404, content=not_found_res)


@router.get("/api/music/lyrics/search")
async def search_lyrics_multi_source(
    track_name: str = Query(..., description="Tên bài hát cần tìm"),
    artist_name: Optional[str] = Query(None, description="Tên ca sĩ"),
    provider: Optional[str] = Query("all", description="Nguồn: all | lrclib | netease")
):
    """Tìm kiếm lời bài hát trực tuyến từ đa nguồn (LRCLIB Quốc Tế + Netease 163 V-Pop/Châu Á)"""
    cleaned_track = _clean_track_title_for_lyrics(track_name)
    cleaned_artist = _clean_artist_name_for_lyrics(artist_name or "", track_name)
    results = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        # 1. Tìm trên LRCLIB
        if provider in ("all", "lrclib"):
            try:
                q_str = f"{cleaned_track} {cleaned_artist}".strip()
                resp = await client.get("https://lrclib.net/api/search", params={"q": q_str}, headers=headers)
                if resp.status_code == 200:
                    items = resp.json()
                    if isinstance(items, list):
                        for it in items[:6]:
                            synced = it.get("syncedLyrics") or ""
                            plain = it.get("plainLyrics") or ""
                            if synced or plain:
                                results.append({
                                    "id": f"lrclib_{it.get('id')}",
                                    "track_name": it.get("trackName") or cleaned_track,
                                    "artist_name": it.get("artistName") or "",
                                    "album_name": it.get("albumName") or "",
                                    "duration": it.get("duration"),
                                    "is_synced": bool(synced),
                                    "synced_lyrics": synced,
                                    "plain_lyrics": plain,
                                    "source": "LRCLIB Quốc Tế"
                                })
            except Exception as e:
                LOGGER.debug(f"[Search LRCLIB] Error: {e}")

        # 2. Tìm trên Netease 163 Cloud Music (Cực mạnh cho Nhạc Việt & Châu Á)
        if provider in ("all", "netease"):
            try:
                n_query = f"{cleaned_track} {cleaned_artist}".strip()
                n_headers = headers.copy()
                n_headers["Referer"] = "https://music.163.com/"
                n_resp = await client.post(
                    "https://music.163.com/api/cloudsearch/pc",
                    data={"s": n_query, "type": 1, "limit": 6},
                    headers=n_headers
                )
                if n_resp.status_code == 200:
                    n_data = n_resp.json()
                    songs = n_data.get("result", {}).get("songs", [])
                    for song in songs:
                        sid = song.get("id")
                        if not sid:
                            continue
                        r_l = await client.get(
                            "https://music.163.com/api/song/lyric",
                            params={"os": "pc", "id": sid, "lv": -1, "kv": -1, "tv": -1},
                            headers=n_headers
                        )
                        if r_l.status_code == 200:
                            l_json = r_l.json()
                            raw_lrc = l_json.get("lrc", {}).get("lyric", "").strip()
                            if raw_lrc:
                                has_synced = bool(re.search(r'\[\d{1,2}:\d{1,2}', raw_lrc))
                                ar_name = ""
                                if song.get("ar") and isinstance(song["ar"], list) and len(song["ar"]) > 0:
                                    ar_name = song["ar"][0].get("name", "")
                                results.append({
                                    "id": f"netease_{sid}",
                                    "track_name": song.get("name") or cleaned_track,
                                    "artist_name": ar_name or cleaned_artist,
                                    "album_name": (song.get("al") or {}).get("name") or "",
                                    "duration": int(song.get("dt", 0) / 1000) if song.get("dt") else None,
                                    "is_synced": has_synced,
                                    "synced_lyrics": raw_lrc if has_synced else "",
                                    "plain_lyrics": "" if has_synced else raw_lrc,
                                    "source": "Netease 163"
                                })
            except Exception as e:
                LOGGER.debug(f"[Search Netease] Error: {e}")

    # Ưu tiên mục có synced lyrics lên đầu
    results.sort(key=lambda x: (1 if x["is_synced"] else 0), reverse=True)
    return JSONResponse(content={"status": "success", "count": len(results), "items": results})


@router.post("/api/music/lyrics/save")
async def save_custom_lyrics(
    request: Request,
    user: Optional[dict] = Depends(get_current_user)
):
    """Lưu lời bài hát do người dùng chỉnh sửa hoặc dán file .lrc thủ công"""
    try:
        data = await request.json()
        track_name = data.get("track_name", "").strip()
        artist_name = data.get("artist_name", "").strip()
        synced_lyrics = data.get("synced_lyrics", "").strip()
        plain_lyrics = data.get("plain_lyrics", "").strip()
        
        if not track_name:
            raise HTTPException(status_code=400, detail="Thiếu tên bài hát")
            
        cleaned_track = _clean_track_title_for_lyrics(track_name)
        cleaned_artist = _clean_artist_name_for_lyrics(artist_name)
        cache_key = f"{cleaned_track.lower()}__{cleaned_artist.lower()}"
        
        doc_data = {
            "status": "success",
            "track_name": cleaned_track,
            "artist_name": cleaned_artist,
            "synced_lyrics": synced_lyrics,
            "plain_lyrics": plain_lyrics,
            "instrumental": data.get("instrumental", False),
            "is_custom": True,
            "source": "custom_saved"
        }
        
        # Cập nhật cache RAM
        _lyrics_memory_cache[cache_key] = {"data": doc_data, "_cached_at": time.time()}
        
        # Cập nhật Database nếu có
        if db is not None:
            coll = db.get_collection("music_custom_lyrics")
            if coll is not None:
                await coll.update_one(
                    {"_id": cache_key},
                    {"$set": {
                        "track_name": cleaned_track,
                        "artist_name": cleaned_artist,
                        "synced_lyrics": synced_lyrics,
                        "plain_lyrics": plain_lyrics,
                        "updated_by": user.get("username") if user else "anonymous",
                        "updated_at": time.time()
                    }},
                    upsert=True
                )
                
        return JSONResponse(content={
            "status": "success", 
            "message": "Đã lưu lời bài hát .lrc thành công!",
            "data": doc_data
        })
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"[SAVE LYRICS] Lỗi: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


