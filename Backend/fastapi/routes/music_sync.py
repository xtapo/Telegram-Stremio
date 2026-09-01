import asyncio
import json
import time
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse
from Backend.logger import LOGGER

sync_router = APIRouter(tags=["Music Realtime Device Sync"])

def _extract_ip_from_ws(websocket: WebSocket) -> str:
    """Trích xuất client IP từ websocket request headers"""
    headers = websocket.headers
    cf_ip = headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()
    x_fwd = headers.get("x-forwarded-for")
    if x_fwd:
        parts = [p.strip() for p in x_fwd.split(",")]
        if parts and parts[0]:
            return parts[0]
    x_real = headers.get("x-real-ip")
    if x_real:
        return x_real.strip()
    if websocket.client and websocket.client.host:
        return websocket.client.host
    return "127.0.0.1"


class ConnectedDevice:
    def __init__(self, device_id: str, ws: WebSocket, room_id: str, ip: str):
        self.device_id = device_id
        self.ws = ws
        self.room_id = room_id
        self.ip = ip
        self.device_name = "Thiết bị không rõ"
        self.device_type = "desktop"  # mobile, desktop, tv
        self.user_id = None
        self.username = None
        self.is_active_player = False
        self.last_seen = time.time()
        self.current_state = {
            "is_playing": False,
            "current_time": 0,
            "duration": 0,
            "volume": 1.0,
            "album_id": None,
            "track_index": 0,
            "track": None,
            "updated_at": time.time()
        }

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "user_id": self.user_id,
            "username": self.username,
            "is_active_player": self.is_active_player,
            "last_seen": self.last_seen,
            "current_state": self.current_state
        }


class MusicSyncHub:
    def __init__(self):
        # rooms: { room_id: { device_id: ConnectedDevice } }
        self.rooms: Dict[str, Dict[str, ConnectedDevice]] = {}
        # pair_codes: { pair_code: { room_id, created_at } }
        self.pair_codes: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def get_room_id(self, user_id: Optional[str], pair_code: Optional[str], client_ip: str) -> str:
        if user_id:
            return f"user_{user_id}"
        if pair_code and pair_code in self.pair_codes:
            return self.pair_codes[pair_code]["room_id"]
        # Nếu không có user_id hoặc pair_code, gom nhóm theo mạng LAN IP
        return f"lan_{client_ip}"

    async def register_device(self, device: ConnectedDevice):
        async with self._lock:
            if device.room_id not in self.rooms:
                self.rooms[device.room_id] = {}
            self.rooms[device.room_id][device.device_id] = device
        LOGGER.info(f"[MUSIC SYNC] Registered device '{device.device_name}' ({device.device_id}) in room '{device.room_id}'")
        await self.broadcast_devices(device.room_id)

    async def unregister_device(self, room_id: str, device_id: str):
        async with self._lock:
            if room_id in self.rooms and device_id in self.rooms[room_id]:
                del self.rooms[room_id][device_id]
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
        LOGGER.info(f"[MUSIC SYNC] Unregistered device ({device_id}) from room '{room_id}'")
        await self.broadcast_devices(room_id)

    def get_devices_list(self, room_id: str) -> List[dict]:
        if room_id not in self.rooms:
            return []
        return [dev.to_dict() for dev in self.rooms[room_id].values()]

    async def broadcast(self, room_id: str, message: dict, exclude_device_id: Optional[str] = None):
        if room_id not in self.rooms:
            return
        dead_devices = []
        payload_str = json.dumps(message)
        for dev_id, dev in list(self.rooms[room_id].items()):
            if exclude_device_id and dev_id == exclude_device_id:
                continue
            try:
                await dev.ws.send_text(payload_str)
            except Exception:
                dead_devices.append(dev_id)

        for dev_id in dead_devices:
            await self.unregister_device(room_id, dev_id)

    async def send_to_device(self, room_id: str, target_device_id: str, message: dict) -> bool:
        if room_id not in self.rooms or target_device_id not in self.rooms[room_id]:
            return False
        target_dev = self.rooms[room_id][target_device_id]
        try:
            await target_dev.ws.send_text(json.dumps(message))
            return True
        except Exception:
            await self.unregister_device(room_id, target_device_id)
            return False

    async def broadcast_devices(self, room_id: str):
        devices = self.get_devices_list(room_id)
        msg = {
            "type": "DEVICES_UPDATE",
            "devices": devices,
            "timestamp": time.time()
        }
        await self.broadcast(room_id, msg)


# Singleton Instance
hub = MusicSyncHub()


@sync_router.websocket("/ws/music-sync")
async def music_sync_websocket_endpoint(
    websocket: WebSocket,
    device_id: Optional[str] = None,
    user_id: Optional[str] = None,
    pair_code: Optional[str] = None
):
    await websocket.accept()
    client_ip = _extract_ip_from_ws(websocket)

    # Lấy session user nếu có
    if not user_id:
        try:
            session_uid = websocket.session.get("music_user_id")
            if session_uid:
                user_id = session_uid
        except Exception:
            pass

    actual_device_id = device_id or f"dev_{int(time.time()*1000)}"
    room_id = hub.get_room_id(user_id, pair_code, client_ip)

    device = ConnectedDevice(actual_device_id, websocket, room_id, client_ip)
    device.user_id = user_id

    try:
        # Gửi thông báo kết nối thành công & cấu hình ban đầu
        await websocket.send_text(json.dumps({
            "type": "INIT_STATE",
            "device_id": actual_device_id,
            "room_id": room_id,
            "devices": hub.get_devices_list(room_id)
        }))

        await hub.register_device(device)

        while True:
            data = await websocket.receive_text()
            if not data:
                continue

            try:
                msg = json.loads(data)
            except Exception:
                continue

            msg_type = msg.get("type", "")
            payload = msg.get("payload", {})

            device.last_seen = time.time()

            if msg_type == "REGISTER":
                # Client cập nhật thông tin thiết bị
                device.device_name = payload.get("device_name", device.device_name)
                device.device_type = payload.get("device_type", device.device_type)
                device.is_active_player = payload.get("is_active_player", device.is_active_player)
                if "current_state" in payload and isinstance(payload["current_state"], dict):
                    device.current_state.update(payload["current_state"])
                if payload.get("user_id"):
                    device.user_id = payload.get("user_id")
                if payload.get("username"):
                    device.username = payload.get("username")
                await hub.broadcast_devices(room_id)

            elif msg_type == "STATE_UPDATE":
                # Thiết bị đang phát gửi tiến trình thời gian thực
                device.is_active_player = payload.get("is_active_player", True)
                device.current_state.update(payload)
                device.current_state["updated_at"] = time.time()

                # Broadcast trạng thái phát tới tất cả các thiết bị khác trong cùng phòng
                broadcast_msg = {
                    "type": "PLAYBACK_STATE",
                    "from_device_id": device.device_id,
                    "from_device_name": device.device_name,
                    "state": device.current_state,
                    "timestamp": time.time()
                }
                await hub.broadcast(room_id, broadcast_msg, exclude_device_id=device.device_id)

            elif msg_type == "COMMAND":
                # Gửi lệnh điều khiển tới thiết bị đích
                target_device_id = msg.get("target_device_id")
                command_name = msg.get("command")  # PLAY_TRACK, PAUSE, RESUME, SEEK, SET_VOLUME, NEXT, PREV, TRANSFER
                
                cmd_msg = {
                    "type": "EXEC_COMMAND",
                    "command": command_name,
                    "from_device_id": device.device_id,
                    "from_device_name": device.device_name,
                    "payload": payload,
                    "timestamp": time.time()
                }

                if target_device_id:
                    await hub.send_to_device(room_id, target_device_id, cmd_msg)
                else:
                    # Broadcast cho tất cả thiết bị khác
                    await hub.broadcast(room_id, cmd_msg, exclude_device_id=device.device_id)

            elif msg_type == "PING":
                await websocket.send_text(json.dumps({"type": "PONG", "timestamp": time.time()}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        LOGGER.warning(f"[MUSIC SYNC WS] Error for device {actual_device_id}: {e}")
    finally:
        await hub.unregister_device(room_id, actual_device_id)


@sync_router.get("/api/music/sync/devices")
async def get_sync_devices(request: Request, pair_code: Optional[str] = None):
    """API lấy danh sách thiết bị đang online trong room"""
    user_id = None
    try:
        user_id = request.session.get("music_user_id")
    except Exception:
        pass
    
    # Lấy client ip
    cf_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For")
    client_ip = cf_ip.split(",")[0].strip() if cf_ip else (request.client.host if request.client else "127.0.0.1")
    
    room_id = hub.get_room_id(user_id, pair_code, client_ip)
    devices = hub.get_devices_list(room_id)
    return {
        "status": "success",
        "room_id": room_id,
        "device_count": len(devices),
        "devices": devices
    }


@sync_router.post("/api/music/sync/pair-code")
async def create_or_join_pair_code(payload: dict, request: Request):
    """Tạo hoặc xác nhận mã PIN 6 số để kết nối 2 thiết bị khác mạng/chưa đăng nhập"""
    code = payload.get("code")
    action = payload.get("action", "generate")  # generate, join
    
    if action == "generate":
        import random
        new_code = f"{random.randint(100000, 999999)}"
        hub.pair_codes[new_code] = {
            "room_id": f"pair_{new_code}",
            "created_at": time.time()
        }
        return {"status": "success", "pair_code": new_code, "room_id": f"pair_{new_code}"}
    
    elif action == "join":
        if not code or code not in hub.pair_codes:
            raise HTTPException(status_code=404, detail="Mã kết nối không hợp lệ hoặc đã hết hạn.")
        return {"status": "success", "pair_code": code, "room_id": hub.pair_codes[code]["room_id"]}
    
    return {"status": "error", "message": "Hành động không hợp lệ"}
