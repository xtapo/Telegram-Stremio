import os
from typing import Dict

from Backend.helper.music_cache import BLOCK_SIZE as AUDIO_CACHE_BLOCK_SIZE

MUSIC_DIR = os.path.abspath("Music")
MUSIC_DATA_DIR = os.path.join(MUSIC_DIR, "data")
os.makedirs(MUSIC_DATA_DIR, exist_ok=True)
LIBRARY_CACHE_FILE = os.path.join(MUSIC_DATA_DIR, "telegram_library.json")
LEGACY_LIBRARY_CACHE_FILE = os.path.join(MUSIC_DIR, "telegram_library.json")
AUDIO_CACHE_DIR = os.path.join(MUSIC_DIR, "cache")
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)
WARM_CACHE_PREFETCH_BYTES = 4 * AUDIO_CACHE_BLOCK_SIZE
_WARM_CACHE_PREFETCH_INFLIGHT: set[str] = set()

_cover_cache: Dict[str, tuple] = {}
_COVER_CACHE_TTL = 86400


# Color palette presets for dynamic vinyl glow
GLOW_PRESETS = [
    {"glow1": "radial-gradient(circle, #f59e0b 0%, #b45309 60%, transparent 80%)", "glow2": "radial-gradient(circle, #ff6dc4 0%, #4338ca 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #0284c7 0%, #0369a1 60%, transparent 80%)", "glow2": "radial-gradient(circle, #f59e0b 0%, #c2410c 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #38bdf8 0%, #0284c7 60%, transparent 80%)", "glow2": "radial-gradient(circle, #f472b6 0%, #db2777 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #eab308 0%, #a16207 60%, transparent 80%)", "glow2": "radial-gradient(circle, #6366f1 0%, #312e81 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #10b981 0%, #047857 60%, transparent 80%)", "glow2": "radial-gradient(circle, #06b6d4 0%, #0e7490 60%, transparent 80%)"},
    {"glow1": "radial-gradient(circle, #8b5cf6 0%, #6d28d9 60%, transparent 80%)", "glow2": "radial-gradient(circle, #ec4899 0%, #be185d 60%, transparent 80%)"},
]
