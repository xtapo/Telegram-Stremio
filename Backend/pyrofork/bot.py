from pyrogram import Client

from Backend.config import Telegram

#----- Primary bot client (loads plugins)
StreamBot = Client(
    name='bot',
    api_id=Telegram.API_ID,
    api_hash=Telegram.API_HASH,
    bot_token=Telegram.BOT_TOKEN,
    plugins={"root": "Backend/pyrofork/plugins"},
    sleep_threshold=20,
    workers=6,
    max_concurrent_transmissions=10
)

USERBOT_CLIENT_INDEX = -1

#----- Userbot client — built at runtime via build_userbot() from the stored session
Userbot = None

#----- Multi-Userbot client registry (user_id -> Client)
multi_userbots = {}

#----- Shared multi-client registries
multi_clients = {}
work_loads = {}
client_dc_map = {}
client_failures = {}
client_avg_mbps = {}


#----- Build (and register) the Userbot client from a session string at runtime
def build_userbot(session_string: str, user_id: int = None, name: str = None):
    global Userbot
    c_name = name or (f"userbot_{user_id}" if user_id else "userbot")
    client = Client(
        name=c_name,
        api_id=Telegram.API_ID,
        api_hash=Telegram.API_HASH,
        session_string=session_string,
        sleep_threshold=20,
        workers=6,
        max_concurrent_transmissions=10,
        no_updates=True,
        in_memory=True,
    )
    if user_id:
        multi_userbots[user_id] = client
    if Userbot is None or not getattr(Userbot, "is_connected", False):
        Userbot = client

    work_loads[USERBOT_CLIENT_INDEX] = 0
    client_failures[USERBOT_CLIENT_INDEX] = 0
    client_avg_mbps[USERBOT_CLIENT_INDEX] = 0.0
    return client


def register_userbot(user_id: int, client: Client):
    global Userbot
    multi_userbots[user_id] = client
    if Userbot is None or not getattr(Userbot, "is_connected", False):
        Userbot = client
    return client


def unregister_userbot(user_id: int):
    global Userbot
    client = multi_userbots.pop(user_id, None)
    if Userbot == client:
        Userbot = next((c for c in multi_userbots.values() if getattr(c, "is_connected", False)), None)
    return client


def get_all_active_userbots():
    return [c for c in multi_userbots.values() if getattr(c, "is_connected", False)]


#----- Resolve the bot's public t.me URL from cached username/me
def get_streambot_url() -> str:
    try:
        username = getattr(StreamBot, "username", None)
        if not username:
            me = getattr(StreamBot, "me", None)
            username = getattr(me, "username", None) if me else None
        if username:
            return f"https://t.me/{username}"
    except Exception:
        pass
    return "https://t.me/"


#----- Per-client workload map ({botN: load}), busiest first; {} when idle
def work_loads_summary() -> dict:
    if not work_loads:
        return {}
    return {
        f"bot{c + 1}": load
        for c, (_, load) in enumerate(sorted(work_loads.items(), key=lambda x: x[1], reverse=True))
    }


if Userbot is not None:
    work_loads[USERBOT_CLIENT_INDEX] = 0
    client_failures[USERBOT_CLIENT_INDEX] = 0
    client_avg_mbps[USERBOT_CLIENT_INDEX] = 0.0
