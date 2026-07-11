"""
Video composition / rendering (PRD 5.2 step 5).

Cuts the selected highlight clips from the source video, concatenates them
with short crossfades, overlays a background music track (ducked under the
original clip audio), and renders the final mp4.

NOTE: this is a functional first pass using moviepy for clarity. If render
time becomes a bottleneck during the hackathon, swap the concat/crossfade
step for a raw ffmpeg filter-graph command (tracked as a follow-up).
"""

from __future__ import annotations

from pathlib import Path

from app.models.schemas import HighlightClip

CROSSFADE_SECONDS = 0.5
MUSIC_VOLUME = 0.7
ORIGINAL_AUDIO_DUCK_VOLUME = 0.4


def render_highlight_reel(
    source_video_path: Path,
    clips: list[HighlightClip],
    output_path: Path,
    music_track_path: Path | None = None,
) -> float:
    """Render the final highlight reel and return its duration in seconds."""
    from moviepy.editor import (  # local import: heavy dependency
        AudioFileClip,
        CompositeAudioClip,
        VideoFileClip,
        concatenate_videoclips,
    )

    if not clips:
        raise ValueError("No highlight clips selected; cannot render an empty reel")

    source = VideoFileClip(str(source_video_path))
    try:
        subclips = [
            source.subclip(clip.start_seconds, clip.end_seconds).audio_fadein(CROSSFADE_SECONDS)
            for clip in clips
        ]
        reel = concatenate_videoclips(subclips, method="compose", padding=-CROSSFADE_SECONDS)
        reel = reel.volumex(ORIGINAL_AUDIO_DUCK_VOLUME) if reel.audio else reel

        if music_track_path is not None and music_track_path.exists():
            music = AudioFileClip(str(music_track_path)).volumex(MUSIC_VOLUME)
            music = music.set_duration(reel.duration) if music.duration >= reel.duration else music.loop(
                duration=reel.duration
            )
            mixed_audio = CompositeAudioClip([reel.audio, music]) if reel.audio else music
            reel = reel.set_audio(mixed_audio)

        reel.write_videofile(
            str(output_path),
            codec="libx264",
            audio_codec="aac",
            fps=source.fps or 30,
            logger=None,
        )
        duration = reel.duration
        reel.close()
        return duration
    finally:
        source.close()
