"""
Video composition / rendering (PRD 5.2 step 5).

Cuts selected highlight clips and concatenates them with ffmpeg.
When a background music track is provided, original clip audio is mixed
under the music (ducked) so both are audible in the final reel.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from app.models.schemas import HighlightClip

logger = logging.getLogger(__name__)

ENCODE_PRESET = "ultrafast"
ENCODE_CRF = "23"
ORIGINAL_AUDIO_VOLUME = 0.45
MUSIC_VOLUME = 0.65


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")


def _probe_duration_seconds(video_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _has_audio_stream(video_path: Path) -> bool:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def render_highlight_reel(
    source_video_path: Path,
    clips: list[HighlightClip],
    output_path: Path,
    music_track_path: Path | None = None,
) -> float:
    """Render the final highlight reel via ffmpeg and return duration in seconds."""
    if not clips:
        raise ValueError("No highlight clips selected; cannot render an empty reel")

    with tempfile.TemporaryDirectory(prefix="clipcoach_render_") as tmp:
        tmp_dir = Path(tmp)
        segment_paths: list[Path] = []

        for index, clip in enumerate(clips):
            segment_path = tmp_dir / f"seg_{index:03d}.mp4"
            duration = max(0.1, clip.end_seconds - clip.start_seconds)
            # Seek before opening the input so ffmpeg does not decode from t=0
            # for every clip (was the main reason 11-min AV1 jobs took 20+ min).
            _run_ffmpeg(
                [
                    "-ss",
                    f"{clip.start_seconds:.3f}",
                    "-i",
                    str(source_video_path),
                    "-t",
                    f"{duration:.3f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    ENCODE_PRESET,
                    "-crf",
                    ENCODE_CRF,
                    "-c:a",
                    "aac",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-movflags",
                    "+faststart",
                    str(segment_path),
                ]
            )
            segment_paths.append(segment_path)

        concat_list = tmp_dir / "concat.txt"
        concat_list.write_text(
            "".join(f"file '{path.resolve()}'\n" for path in segment_paths),
            encoding="utf-8",
        )

        concat_path = tmp_dir / "concat.mp4"
        _run_ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(concat_path),
            ]
        )

        if music_track_path is not None and music_track_path.exists():
            _mix_original_with_music(concat_path, music_track_path, output_path)
        else:
            output_path.write_bytes(concat_path.read_bytes())

    duration = _probe_duration_seconds(output_path)
    logger.info(
        "Rendered highlight reel duration=%.1fs clips=%d music=%s",
        duration,
        len(clips),
        music_track_path.name if music_track_path else "none",
    )
    return duration


def _mix_original_with_music(video_path: Path, music_path: Path, output_path: Path) -> None:
    """Overlay ducked original audio with looping background music."""
    has_original_audio = _has_audio_stream(video_path)

    if has_original_audio:
        filter_complex = (
            f"[0:a]volume={ORIGINAL_AUDIO_VOLUME}[a0];"
            f"[1:a]volume={MUSIC_VOLUME}[a1];"
            "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
        )
        args = [
            "-i",
            str(video_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
    else:
        # No game audio — still attach the selected music track.
        args = [
            "-i",
            str(video_path),
            "-stream_loop",
            "-1",
            "-i",
            str(music_path),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]

    _run_ffmpeg(args)
