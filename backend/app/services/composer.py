"""
Video composition / rendering (PRD 5.2 step 5).

Cuts selected highlight clips and concatenates them with ffmpeg.
Uses input seeking (`-ss` before `-i`) so we do not re-decode the entire
source for every clip — critical for long AV1/H.265 uploads.
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
            _run_ffmpeg(
                [
                    "-i",
                    str(concat_path),
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(music_track_path),
                    "-filter_complex",
                    "[0:a]volume=0.4[a0];[1:a]volume=0.7[a1];"
                    "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
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
            )
        else:
            output_path.write_bytes(concat_path.read_bytes())

    duration = _probe_duration_seconds(output_path)
    logger.info("Rendered highlight reel duration=%.1fs clips=%d", duration, len(clips))
    return duration
