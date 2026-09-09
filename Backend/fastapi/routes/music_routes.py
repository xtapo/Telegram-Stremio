"""Compatibility facade for the music HTTP domains.

Implementation lives in ``Backend.fastapi.routes.music``. Existing callers can
keep importing established seams from this module while new code should depend
on the owning domain module directly.
"""

from fastapi import APIRouter

from Backend.fastapi.routes.music.audio import (
    _format_duration, _format_size, deduplicate_tracks, detect_audio_quality, detect_audio_quality_from_track_info,
    detect_country_from_track_info, detect_genre_from_track_info, detect_year_from_track_info,
    probe_audio_metadata,
)
from Backend.fastapi.routes.music.common import GLOW_PRESETS
from Backend.fastapi.routes.music.backup import _build_music_backup_data, _perform_music_restore, router as backup_router
from Backend.fastapi.routes.music.catalog import (
    MusicShazamManager, get_all_artists, invalidate_artists_cache, music_shazam_manager, router as catalog_router,
)
from Backend.fastapi.routes.music.gdrive import router as gdrive_router
from Backend.fastapi.routes.music.lyrics import router as lyrics_router
from Backend.fastapi.routes.music.pages import router as pages_router
from Backend.fastapi.routes.music.playlists import (
    _build_m3u8_content, _get_request_base_url, _load_playlists_file, _safe_content_disposition,
    _save_playlists_file, router as playlists_router,
)
from Backend.fastapi.routes.music.scan import (
    MusicAutoSyncManager, MusicScanManager, music_auto_sync_manager, music_scan_manager,
    notify_music_auto_sync, router as scan_router,
)
from Backend.fastapi.routes.music.storage import (
    _db_load_channels, _db_load_library, _db_save_channels, _db_save_library,
    _db_update_channel_progress, _startup_preload_library, generate_album_id,
)
from Backend.fastapi.routes.music.streaming import router as streaming_router

router = APIRouter(tags=["Music Player & Telegram Storage"])
for domain_router in (
    pages_router, playlists_router, scan_router, streaming_router, catalog_router,
    lyrics_router, gdrive_router, backup_router,
):
    router.include_router(domain_router)

__all__ = [
    "router", "_startup_preload_library", "_db_load_library", "_db_save_library",
    "_db_load_channels", "_db_save_channels", "_db_update_channel_progress",
    "_get_request_base_url", "_safe_content_disposition", "_build_m3u8_content",
    "_load_playlists_file", "_save_playlists_file", "_build_music_backup_data",
    "_perform_music_restore", "notify_music_auto_sync", "probe_audio_metadata",
    "detect_audio_quality", "detect_audio_quality_from_track_info", "detect_genre_from_track_info",
    "detect_country_from_track_info", "detect_year_from_track_info", "deduplicate_tracks",
    "GLOW_PRESETS", "_format_duration", "_format_size",
    "generate_album_id", "get_all_artists", "MusicScanManager", "MusicAutoSyncManager",
    "MusicShazamManager", "music_scan_manager", "music_auto_sync_manager", "music_shazam_manager",
]
