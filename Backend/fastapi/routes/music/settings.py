"""Public, non-sensitive settings needed by the music player."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from Backend.helper.settings_manager import SettingsManager

router = APIRouter(tags=["Music Player & Telegram Storage"])


@router.get("/api/music/player-settings")
async def get_music_player_settings():
    settings = SettingsManager.current()
    return JSONResponse(
        content={
            "status": "success",
            "settings": {
                "music_tracklist_page_size": settings.music_tracklist_page_size,
                "music_mobile_tracklist_page_size": settings.music_mobile_tracklist_page_size,
            },
        },
        headers={"Cache-Control": "no-store"},
    )
