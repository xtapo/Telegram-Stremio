import asyncio
import json
import secrets
import time
from typing import Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from Backend.logger import LOGGER


sync_router = APIRouter(tags=["Music Realtime Device Sync"])

DEVICE_TTL_SECONDS = 22
COMMAND_TTL_SECONDS = 35
PAIR_CODE_TTL_SECONDS = 10 * 60
PAIR_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60
MAX_PENDING_COMMANDS_PER_DEVICE = 50

SUPPORTED_COMMANDS = {
    "PLAY_TRACK",
    "PAUSE",
    "RESUME",
    "TOGGLE_PLAY",
    "SEEK",
    "SET_VOLUME",
    "NEXT",
    "PREV",
    "TRANSFER",
}


def _extract_ip_from_ws(websocket: WebSocket) -> str:
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


def _extract_ip_from_request(request: Request) -> str:
    forwarded = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def _session_user_id(request: Request, fallback: Optional[str] = None) -> Optional[str]:
    try:
        session_uid = request.session.get("music_user_id")
        if session_uid is not None:
            return str(session_uid)
    except Exception:
        pass
    return str(fallback) if fallback else None


def _clean_state(raw_state: Optional[dict]) -> dict:
    raw_state = raw_state if isinstance(raw_state, dict) else {}
    try:
        current_time = max(0.0, float(raw_state.get("current_time") or 0))
    except (TypeError, ValueError):
        current_time = 0.0
    try:
        duration = max(0.0, float(raw_state.get("duration") or 0))
    except (TypeError, ValueError):
        duration = 0.0
    try:
        volume = max(0.0, min(1.0, float(raw_state.get("volume", 1.0))))
    except (TypeError, ValueError):
        volume = 1.0
    try:
        track_index = int(raw_state.get("track_index") or 0)
    except (TypeError, ValueError):
        track_index = 0

    return {
        "is_playing": bool(raw_state.get("is_playing", False)),
        "current_time": current_time,
        "duration": duration,
        "volume": volume,
        "album_id": raw_state.get("album_id"),
        "track_index": track_index,
        "track": raw_state.get("track") if isinstance(raw_state.get("track"), dict) else None,
        "updated_at": time.time(),
    }


class ConnectedDevice:
    def __init__(self, device_id: str, ws: WebSocket, room_id: str, ip: str):
        self.device_id = device_id
        self.ws = ws
        self.room_id = room_id
        self.ip = ip
        self.device_name = "Thiết bị không rõ"
        self.device_type = "desktop"
        self.user_id = None
        self.username = None
        self.is_active_player = False
        self.last_seen = time.time()
        self.current_state = _clean_state({})

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "user_id": self.user_id,
            "username": self.username,
            "is_active_player": self.is_active_player,
            "last_seen": self.last_seen,
            "current_state": self.current_state,
        }


class MusicSyncHub:
    def __init__(self):
        self.rooms: Dict[str, Dict[str, ConnectedDevice]] = {}
        self.rest_devices: Dict[str, Dict[str, dict]] = {}
        self.pending_commands: Dict[str, List[dict]] = {}
        self.pair_codes: Dict[str, dict] = {}
        self.pair_tokens: Dict[str, dict] = {}
        self.room_states: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _room_state(self, room_id: str) -> dict:
        if room_id not in self.room_states:
            self.room_states[room_id] = {
                "active_device_id": None,
                "playback_state": _clean_state({}),
                "playback_context": None,
                "revision": 0,
                "updated_at": time.time(),
            }
        return self.room_states[room_id]

    def _touch_revision(self, room_id: str) -> int:
        room_state = self._room_state(room_id)
        room_state["revision"] += 1
        room_state["updated_at"] = time.time()
        return room_state["revision"]

    def _cleanup_pair_codes(self) -> None:
        now = time.time()
        expired = [code for code, info in self.pair_codes.items() if info.get("expires_at", 0) <= now]
        for code in expired:
            self.pair_codes.pop(code, None)

    def pair_code_info(self, pair_code: Optional[str]) -> Optional[dict]:
        if not pair_code:
            return None
        self._cleanup_pair_codes()
        return self.pair_codes.get(str(pair_code))

    def pair_token_info(self, pair_token: Optional[str]) -> Optional[dict]:
        if not pair_token:
            return None
        info = self.pair_tokens.get(str(pair_token))
        if not info:
            return None
        if info.get("expires_at", 0) <= time.time():
            self.pair_tokens.pop(str(pair_token), None)
            return None
        return info

    def create_pair_token(self, room_id: str) -> dict:
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + PAIR_TOKEN_TTL_SECONDS
        self.pair_tokens[token] = {"room_id": room_id, "expires_at": expires_at}
        return {"pair_token": token, "pair_token_expires_at": expires_at}

    def get_room_id(
        self,
        user_id: Optional[str],
        pair_code: Optional[str],
        client_ip: str,
        pair_token: Optional[str] = None,
    ) -> str:
        token_info = self.pair_token_info(pair_token)
        if token_info:
            return token_info["room_id"]
        pair_info = self.pair_code_info(pair_code)
        if pair_info:
            return pair_info["room_id"]
        if user_id:
            return f"user_{user_id}"
        return f"lan_{client_ip}"

    def create_pair_code(self, room_id: str, device_id: Optional[str]) -> dict:
        self._cleanup_pair_codes()
        for _ in range(20):
            code = f"{secrets.randbelow(900000) + 100000}"
            if code not in self.pair_codes:
                break
        else:
            raise RuntimeError("Unable to allocate pair code")
        expires_at = time.time() + PAIR_CODE_TTL_SECONDS
        self.pair_codes[code] = {
            "room_id": room_id,
            "created_at": time.time(),
            "expires_at": expires_at,
            "device_id": device_id,
        }
        return {"pair_code": code, "room_id": room_id, "expires_at": expires_at}

    async def register_device(self, device: ConnectedDevice):
        async with self._lock:
            self.rooms.setdefault(device.room_id, {})[device.device_id] = device
            self._room_state(device.room_id)
        LOGGER.info(
            f"[MUSIC SYNC] Registered device '{device.device_name}' ({device.device_id}) in room '{device.room_id}'"
        )
        await self.broadcast_devices(device.room_id)

    async def unregister_device(self, room_id: str, device_id: str):
        async with self._lock:
            if room_id in self.rooms:
                self.rooms[room_id].pop(device_id, None)
                if not self.rooms[room_id]:
                    self.rooms.pop(room_id, None)
        self._clear_active_if_offline(room_id)
        await self.broadcast_devices(room_id)

    def _cleanup_rest_devices(self, room_id: str) -> None:
        if room_id not in self.rest_devices:
            return
        now = time.time()
        expired = [
            device_id
            for device_id, device in self.rest_devices[room_id].items()
            if now - device.get("last_seen", 0) > DEVICE_TTL_SECONDS
        ]
        for device_id in expired:
            self.rest_devices[room_id].pop(device_id, None)
        if not self.rest_devices[room_id]:
            self.rest_devices.pop(room_id, None)

    def _clear_active_if_offline(self, room_id: str) -> None:
        room_state = self._room_state(room_id)
        active_id = room_state.get("active_device_id")
        if not active_id:
            return
        online_ids = {d.get("device_id") for d in self.get_devices_list(room_id, reconcile=False)}
        if active_id not in online_ids:
            room_state["active_device_id"] = None
            self._touch_revision(room_id)

    def update_rest_device(self, room_id: str, device_info: dict):
        device_id = device_info.get("device_id")
        if not device_id:
            return

        self._cleanup_rest_devices(room_id)
        now = time.time()
        device_info["last_seen"] = now
        device_info["current_state"] = _clean_state(device_info.get("current_state"))
        self.rest_devices.setdefault(room_id, {})[device_id] = device_info

        room_state = self._room_state(room_id)
        active_id = room_state.get("active_device_id")
        wants_active = bool(device_info.get("is_active_player"))

        if active_id is None and wants_active:
            room_state["active_device_id"] = device_id
            active_id = device_id
            self._touch_revision(room_id)

        if active_id == device_id:
            device_info["is_active_player"] = True
            room_state["playback_state"] = dict(device_info["current_state"])
            room_state["updated_at"] = now
        else:
            device_info["is_active_player"] = False

        self._clear_active_if_offline(room_id)

    def update_ws_device_state(self, room_id: str, device: ConnectedDevice, state: Optional[dict], wants_active: bool):
        device.current_state = _clean_state(state)
        room_state = self._room_state(room_id)
        active_id = room_state.get("active_device_id")
        if active_id is None and wants_active:
            room_state["active_device_id"] = device.device_id
            active_id = device.device_id
            self._touch_revision(room_id)
        device.is_active_player = active_id == device.device_id
        if device.is_active_player:
            room_state["playback_state"] = dict(device.current_state)
            room_state["updated_at"] = time.time()

    def set_active_device(self, room_id: str, device_id: str, state_hint: Optional[dict] = None):
        room_state = self._room_state(room_id)
        if room_state.get("active_device_id") != device_id:
            room_state["active_device_id"] = device_id
            self._touch_revision(room_id)

        if isinstance(state_hint, dict):
            current = dict(room_state.get("playback_state") or _clean_state({}))
            current.update(state_hint)
            room_state["playback_state"] = _clean_state(current)
            room_state["updated_at"] = time.time()

        if room_id in self.rest_devices:
            for dev_id, dev in self.rest_devices[room_id].items():
                dev["is_active_player"] = dev_id == device_id
        if room_id in self.rooms:
            for dev_id, dev in self.rooms[room_id].items():
                dev.is_active_player = dev_id == device_id

    def apply_command_prediction(self, room_id: str, target_device_id: str, command: str, payload: dict):
        room_state = self._room_state(room_id)
        state = dict(room_state.get("playback_state") or _clean_state({}))

        if command in {"TRANSFER", "PLAY_TRACK"}:
            hint = {
                "is_playing": payload.get("is_playing", True),
                "current_time": payload.get("seek_time", 0),
                "album_id": payload.get("album_id"),
                "track_index": payload.get("track_index", 0),
                "track": payload.get("track"),
            }
            room_state["playback_context"] = {
                "album_id": payload.get("album_id"),
                "album_title": payload.get("album_title"),
                "album_artist": payload.get("album_artist"),
                "album_cover": payload.get("album_cover"),
                "track_index": payload.get("track_index", 0),
                "tracks": payload.get("tracks") if isinstance(payload.get("tracks"), list) else [],
            }
            self.set_active_device(room_id, target_device_id, hint)
            return

        if room_state.get("active_device_id") != target_device_id:
            return
        if command == "PAUSE":
            state["is_playing"] = False
        elif command == "RESUME":
            state["is_playing"] = True
        elif command == "TOGGLE_PLAY":
            state["is_playing"] = not bool(state.get("is_playing"))
        elif command == "SEEK" and payload.get("position") is not None:
            state["current_time"] = max(0.0, float(payload.get("position") or 0))
        elif command == "SET_VOLUME" and payload.get("volume") is not None:
            state["volume"] = max(0.0, min(1.0, float(payload.get("volume") or 0)))
        else:
            return
        room_state["playback_state"] = _clean_state(state)
        self._touch_revision(room_id)

    def get_devices_list(self, room_id: str, reconcile: bool = True) -> List[dict]:
        self._cleanup_rest_devices(room_id)
        combined: Dict[str, dict] = {}

        if room_id in self.rooms:
            for device_id, device in self.rooms[room_id].items():
                combined[device_id] = device.to_dict()

        if room_id in self.rest_devices:
            for device_id, device in self.rest_devices[room_id].items():
                if device_id not in combined:
                    combined[device_id] = dict(device)

        if reconcile:
            room_state = self._room_state(room_id)
            active_id = room_state.get("active_device_id")
            if active_id and active_id not in combined:
                room_state["active_device_id"] = None
                active_id = None
                self._touch_revision(room_id)
            for device_id, device in combined.items():
                device["is_active_player"] = bool(active_id and device_id == active_id)

        return list(combined.values())

    def room_snapshot(self, room_id: str) -> dict:
        devices = self.get_devices_list(room_id)
        state = self._room_state(room_id)
        return {
            "room_id": room_id,
            "devices": devices,
            "active_device_id": state.get("active_device_id"),
            "playback_state": state.get("playback_state"),
            "playback_context": state.get("playback_context"),
            "revision": state.get("revision", 0),
            "updated_at": state.get("updated_at"),
        }

    def ack_commands(self, device_id: str, command_ids: Set[str]) -> None:
        if not command_ids or device_id not in self.pending_commands:
            return
        self.pending_commands[device_id] = [
            item for item in self.pending_commands[device_id] if item.get("command_id") not in command_ids
        ]
        if not self.pending_commands[device_id]:
            self.pending_commands.pop(device_id, None)

    def get_pending_commands(self, device_id: str) -> List[dict]:
        now = time.time()
        queue = [
            item
            for item in self.pending_commands.get(device_id, [])
            if item.get("_expires_at", 0) > now
        ]
        if queue:
            self.pending_commands[device_id] = queue
        else:
            self.pending_commands.pop(device_id, None)

        return [{key: value for key, value in item.items() if not key.startswith("_")} for item in queue]

    async def queue_command(self, room_id: str, target_device_id: Optional[str], command_data: dict) -> List[str]:
        devices = {d.get("device_id") for d in self.get_devices_list(room_id)}
        from_device_id = command_data.get("from_device_id")
        targets = [target_device_id] if target_device_id else [d for d in devices if d and d != from_device_id]
        queued_ids: List[str] = []

        for target_id in targets:
            if not target_id or target_id not in devices:
                continue
            command_id = secrets.token_urlsafe(12)
            queued = dict(command_data)
            queued["command_id"] = command_id
            queued["target_device_id"] = target_id
            queued["_expires_at"] = time.time() + COMMAND_TTL_SECONDS
            queue = self.pending_commands.setdefault(target_id, [])
            queue.append(queued)
            if len(queue) > MAX_PENDING_COMMANDS_PER_DEVICE:
                del queue[:-MAX_PENDING_COMMANDS_PER_DEVICE]
            queued_ids.append(command_id)
            await self.send_to_device(room_id, target_id, {k: v for k, v in queued.items() if not k.startswith("_")})

        return queued_ids

    async def broadcast(self, room_id: str, message: dict, exclude_device_id: Optional[str] = None):
        if room_id not in self.rooms:
            return
        dead_devices = []
        payload_str = json.dumps(message)
        for device_id, device in list(self.rooms[room_id].items()):
            if exclude_device_id and device_id == exclude_device_id:
                continue
            try:
                await device.ws.send_text(payload_str)
            except Exception:
                dead_devices.append(device_id)
        for device_id in dead_devices:
            if room_id in self.rooms:
                self.rooms[room_id].pop(device_id, None)

    async def send_to_device(self, room_id: str, target_device_id: str, message: dict) -> bool:
        if room_id not in self.rooms or target_device_id not in self.rooms[room_id]:
            return False
        target_device = self.rooms[room_id][target_device_id]
        try:
            await target_device.ws.send_text(json.dumps(message))
            return True
        except Exception:
            self.rooms[room_id].pop(target_device_id, None)
            return False

    async def broadcast_devices(self, room_id: str):
        snapshot = self.room_snapshot(room_id)
        await self.broadcast(
            room_id,
            {
                "type": "DEVICES_UPDATE",
                "devices": snapshot["devices"],
                "active_device_id": snapshot["active_device_id"],
                "playback_state": snapshot["playback_state"],
                "revision": snapshot["revision"],
                "timestamp": time.time(),
            },
        )


hub = MusicSyncHub()


@sync_router.websocket("/ws/music-sync")
@sync_router.websocket("/api/music/sync/ws")
@sync_router.websocket("/api/music/ws")
async def music_sync_websocket_endpoint(
    websocket: WebSocket,
    device_id: Optional[str] = None,
    user_id: Optional[str] = None,
    pair_code: Optional[str] = None,
):
    await websocket.accept()
    client_ip = _extract_ip_from_ws(websocket)
    try:
        if hasattr(websocket, "session") and websocket.session is not None:
            session_uid = websocket.session.get("music_user_id")
            if session_uid is not None:
                user_id = str(session_uid)
    except Exception:
        pass

    actual_device_id = device_id or f"dev_{int(time.time() * 1000)}"
    room_id = hub.get_room_id(user_id, pair_code, client_ip)
    device = ConnectedDevice(actual_device_id, websocket, room_id, client_ip)
    device.user_id = user_id

    try:
        snapshot = hub.room_snapshot(room_id)
        await websocket.send_text(json.dumps({"type": "INIT_STATE", "device_id": actual_device_id, **snapshot}))
        await hub.register_device(device)

        while True:
            raw = await websocket.receive_text()
            if not raw:
                continue
            try:
                msg = json.loads(raw)
            except Exception:
                continue

            msg_type = msg.get("type", "")
            payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
            device.last_seen = time.time()

            if msg_type in {"REGISTER", "STATE_UPDATE"}:
                device.device_name = payload.get("device_name", device.device_name)
                device.device_type = payload.get("device_type", device.device_type)
                device.username = payload.get("username", device.username)
                state = payload.get("current_state", payload)
                hub.update_ws_device_state(
                    room_id,
                    device,
                    state,
                    bool(payload.get("is_active_player", msg_type == "STATE_UPDATE")),
                )
                await hub.broadcast_devices(room_id)

            elif msg_type == "COMMAND":
                target_device_id = msg.get("target_device_id")
                command_name = str(msg.get("command") or "").upper()
                if command_name not in SUPPORTED_COMMANDS:
                    continue
                cmd_msg = {
                    "type": "EXEC_COMMAND",
                    "command": command_name,
                    "from_device_id": device.device_id,
                    "from_device_name": device.device_name,
                    "payload": payload,
                    "timestamp": time.time(),
                }
                command_ids = await hub.queue_command(room_id, target_device_id, cmd_msg)
                if target_device_id and command_ids:
                    hub.apply_command_prediction(room_id, target_device_id, command_name, payload)
                await hub.broadcast_devices(room_id)

            elif msg_type == "COMMAND_ACK":
                command_ids = payload.get("command_ids") if isinstance(payload.get("command_ids"), list) else []
                hub.ack_commands(device.device_id, {str(command_id) for command_id in command_ids})

            elif msg_type == "PING":
                await websocket.send_text(json.dumps({"type": "PONG", "timestamp": time.time()}))

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        LOGGER.warning(f"[MUSIC SYNC WS] Error for device {actual_device_id}: {exc}")
    finally:
        await hub.unregister_device(room_id, actual_device_id)


@sync_router.post("/api/music/sync/heartbeat")
async def sync_heartbeat(payload: dict, request: Request):
    device_id = str(payload.get("device_id") or "").strip()
    if not device_id:
        raise HTTPException(status_code=400, detail="Missing device_id")

    user_id = _session_user_id(request, payload.get("user_id"))
    pair_code = str(payload.get("pair_code") or "").strip() or None
    pair_token = str(payload.get("pair_token") or "").strip() or None
    client_ip = _extract_ip_from_request(request)
    room_id = hub.get_room_id(user_id, pair_code, client_ip, pair_token)

    ack_ids = payload.get("ack_command_ids") if isinstance(payload.get("ack_command_ids"), list) else []
    hub.ack_commands(device_id, {str(command_id) for command_id in ack_ids})

    if payload.get("claim_active"):
        hub.set_active_device(room_id, device_id, payload.get("current_state"))

    device_info = {
        "device_id": device_id,
        "device_name": str(payload.get("device_name") or "Thiết bị")[:120],
        "device_type": str(payload.get("device_type") or "desktop")[:24],
        "user_id": user_id,
        "username": payload.get("username"),
        "is_active_player": bool(payload.get("is_active_player", False)),
        "current_state": payload.get("current_state") if isinstance(payload.get("current_state"), dict) else {},
    }
    hub.update_rest_device(room_id, device_info)

    commands = hub.get_pending_commands(device_id)
    snapshot = hub.room_snapshot(room_id)
    pair_info = hub.pair_code_info(pair_code)

    return {
        "status": "success",
        **snapshot,
        "commands": commands,
        "pair_code_valid": bool(pair_info) if pair_code else None,
        "server_time": time.time(),
    }


@sync_router.post("/api/music/sync/command")
async def send_sync_command(payload: dict, request: Request):
    from_device_id = str(payload.get("from_device_id") or "").strip()
    target_device_id = str(payload.get("target_device_id") or "").strip() or None
    command_name = str(payload.get("command") or "").strip().upper()
    command_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}

    if not from_device_id:
        raise HTTPException(status_code=400, detail="Missing from_device_id")
    if command_name not in SUPPORTED_COMMANDS:
        raise HTTPException(status_code=400, detail="Unsupported sync command")
    if not target_device_id:
        raise HTTPException(status_code=400, detail="Missing target_device_id")

    user_id = _session_user_id(request, payload.get("user_id"))
    pair_code = str(payload.get("pair_code") or "").strip() or None
    pair_token = str(payload.get("pair_token") or "").strip() or None
    client_ip = _extract_ip_from_request(request)
    room_id = hub.get_room_id(user_id, pair_code, client_ip, pair_token)
    online_ids = {device.get("device_id") for device in hub.get_devices_list(room_id)}
    if target_device_id not in online_ids:
        raise HTTPException(status_code=404, detail="Thiết bị đích đang ngoại tuyến")

    command_message = {
        "type": "EXEC_COMMAND",
        "command": command_name,
        "from_device_id": from_device_id,
        "from_device_name": str(payload.get("from_device_name") or "Thiết bị điều khiển")[:120],
        "payload": command_payload,
        "timestamp": time.time(),
    }
    command_ids = await hub.queue_command(room_id, target_device_id, command_message)
    if not command_ids:
        raise HTTPException(status_code=404, detail="Thiết bị đích đang ngoại tuyến")

    hub.apply_command_prediction(room_id, target_device_id, command_name, command_payload)
    snapshot = hub.room_snapshot(room_id)
    await hub.broadcast_devices(room_id)
    LOGGER.info(
        f"[MUSIC SYNC REST] Dispatched '{command_name}' from {from_device_id} to {target_device_id} in {room_id}"
    )

    return {
        "status": "success",
        "command_id": command_ids[0],
        "room_id": room_id,
        "active_device_id": snapshot["active_device_id"],
        "revision": snapshot["revision"],
    }


@sync_router.get("/api/music/sync/devices")
async def get_sync_devices(request: Request, pair_code: Optional[str] = None):
    user_id = _session_user_id(request)
    client_ip = _extract_ip_from_request(request)
    room_id = hub.get_room_id(user_id, pair_code, client_ip)
    snapshot = hub.room_snapshot(room_id)
    return {
        "status": "success",
        **snapshot,
        "device_count": len(snapshot["devices"]),
        "server_time": time.time(),
    }


@sync_router.post("/api/music/sync/pair-code")
async def create_or_join_pair_code(payload: dict, request: Request):
    action = str(payload.get("action") or "generate").lower()
    code = str(payload.get("code") or "").strip()
    user_id = _session_user_id(request, payload.get("user_id"))
    client_ip = _extract_ip_from_request(request)

    if action == "generate":
        creator_room = hub.get_room_id(user_id, None, client_ip)
        pair = hub.create_pair_code(creator_room, str(payload.get("device_id") or "") or None)
        return {"status": "success", **pair, "ttl_seconds": PAIR_CODE_TTL_SECONDS}

    if action == "join":
        info = hub.pair_code_info(code)
        if not info:
            raise HTTPException(status_code=404, detail="Mã kết nối không hợp lệ hoặc đã hết hạn.")
        token = hub.create_pair_token(info["room_id"])
        return {
            "status": "success",
            "pair_code": code,
            "room_id": info["room_id"],
            "expires_at": info["expires_at"],
            **token,
        }

    raise HTTPException(status_code=400, detail="Hành động không hợp lệ")
