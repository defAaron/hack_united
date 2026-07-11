"""Music library endpoints — list available background tracks for the UI picker."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import MusicTrackResponse
from app.services.music_catalog import get_music_track, list_music_tracks

router = APIRouter(prefix="/api/music", tags=["music"])


@router.get("", response_model=list[MusicTrackResponse])
async def list_tracks() -> list[MusicTrackResponse]:
    return [
        MusicTrackResponse(id=track.id, title=track.title, preview_url=track.preview_url)
        for track in list_music_tracks()
    ]


@router.get("/{track_id}", response_model=MusicTrackResponse)
async def get_track(track_id: str) -> MusicTrackResponse:
    track = get_music_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail=f"Music track not found: {track_id}")
    return MusicTrackResponse(id=track.id, title=track.title, preview_url=track.preview_url)
