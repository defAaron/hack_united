"""
Royalty-free background music catalog for highlight reels.

Tracks live in `backend/assets/music/`. Add a new file + entry here to expose
it in the UI — no other wiring required.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings

MUSIC_DIR = Path(__file__).resolve().parents[2] / "assets" / "music"


@dataclass(frozen=True)
class MusicTrack:
    id: str
    title: str
    filename: str

    @property
    def path(self) -> Path:
        return MUSIC_DIR / self.filename

    @property
    def preview_url(self) -> str:
        return f"/assets/music/{self.filename}"


# Display titles shown in the UI song picker.
MUSIC_CATALOG: tuple[MusicTrack, ...] = (
    MusicTrack(id="vibehorn", title="Vibehorn", filename="vibehorn.mp3"),
    MusicTrack(id="the-mountain", title="The Mountain", filename="the-mountain.mp3"),
    MusicTrack(id="solarflex-hype", title="Solarflex Hype", filename="solarflex-hype.mp3"),
    MusicTrack(id="mfcc", title="MFCC", filename="mfcc.mp3"),
)


def list_music_tracks() -> list[MusicTrack]:
    """Return catalog entries whose files are present on disk."""
    return [track for track in MUSIC_CATALOG if track.path.exists()]


def get_music_track(track_id: str | None) -> MusicTrack | None:
    if not track_id:
        return None
    for track in MUSIC_CATALOG:
        if track.id == track_id and track.path.exists():
            return track
    return None


def default_music_track() -> MusicTrack | None:
    tracks = list_music_tracks()
    return tracks[0] if tracks else None


def resolve_music_path(track_id: str | None) -> Path | None:
    """Resolve a track id to a filesystem path, falling back to the default track."""
    track = get_music_track(track_id) or default_music_track()
    if track is None:
        return None
    # Keep settings hook for future overrides (e.g. custom music dir).
    _ = get_settings()
    return track.path
