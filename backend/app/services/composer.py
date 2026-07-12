"""
Video composition / rendering (PRD 5.2 step 5).

Cuts selected highlight clips and concatenates them with ffmpeg.
When a background music track is provided, original clip audio is mixed
under the music (ducked) so both are audible in the final reel.

Hosted environments (Railway) have limited RAM — we intentionally render at
a capped resolution and prefer a single-pass filter graph so AV1 sources are
not fully decoded once per clip.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path

from app.core.config import get_settings
from app.models.schemas import HighlightClip
from app.services.media_utils import has_audio_stream, probe_duration_seconds

logger = logging.getLogger(__name__)

ENCODE_PRESET = "ultrafast"
ENCODE_CRF = "28"
ORIGINAL_AUDIO_VOLUME = 0.45
MUSIC_VOLUME = 0.65


def _run_ffmpeg(args: list[str]) -> None:
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        detail = stderr or stdout or "(no ffmpeg output — process may have been OOM-killed)"
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}): {detail[-2000:]}"
        )


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
        concat_path = tmp_dir / "concat.mp4"

        try:
            _render_single_pass(source_video_path, clips, concat_path)
        except RuntimeError as exc:
            logger.warning("Single-pass render failed (%s); falling back to per-clip cuts", exc)
            _render_per_clip(source_video_path, clips, concat_path, tmp_dir)

        if music_track_path is not None and music_track_path.exists():
            _mix_original_with_music(concat_path, music_track_path, output_path)
        else:
            output_path.write_bytes(concat_path.read_bytes())

    duration = probe_duration_seconds(output_path)
    logger.info(
        "Rendered highlight reel duration=%.1fs clips=%d music=%s",
        duration,
        len(clips),
        music_track_path.name if music_track_path else "none",
    )
    return duration


def _scale_filter() -> str:
    height = max(240, int(get_settings().max_render_height))
    return f"scale=-2:'min({height},ih)'"


def _render_single_pass(
    source_video_path: Path, clips: list[HighlightClip], output_path: Path
) -> None:
    """One ffmpeg process: trim all clips, scale, concat — avoids N AV1 re-decodes."""
    has_audio = has_audio_stream(source_video_path)
    filter_parts: list[str] = []
    concat_labels: list[str] = []

    for index, clip in enumerate(clips):
        start = max(0.0, clip.start_seconds)
        end = max(start + 0.1, clip.end_seconds)
        v_label = f"v{index}"
        filter_parts.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS,"
            f"{_scale_filter()}[{v_label}]"
        )
        if has_audio:
            a_label = f"a{index}"
            filter_parts.append(
                f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[{a_label}]"
            )
            concat_labels.extend([f"[{v_label}]", f"[{a_label}]"])
        else:
            concat_labels.append(f"[{v_label}]")

    n = len(clips)
    if has_audio:
        filter_parts.append(
            f"{''.join(concat_labels)}concat=n={n}:v=1:a=1[outv][outa]"
        )
        maps = ["-map", "[outv]", "-map", "[outa]", "-c:a", "aac", "-ac", "2", "-ar", "44100"]
    else:
        filter_parts.append(f"{''.join(concat_labels)}concat=n={n}:v=1:a=0[outv]")
        maps = ["-map", "[outv]", "-an"]

    _run_ffmpeg(
        [
            "-i",
            str(source_video_path),
            "-filter_complex",
            ";".join(filter_parts),
            *maps,
            "-c:v",
            "libx264",
            "-preset",
            ENCODE_PRESET,
            "-crf",
            ENCODE_CRF,
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )


def _render_per_clip(
    source_video_path: Path,
    clips: list[HighlightClip],
    output_path: Path,
    tmp_dir: Path,
) -> None:
    """Fallback: cut each clip individually at capped resolution."""
    segment_paths: list[Path] = []

    for index, clip in enumerate(clips):
        segment_path = tmp_dir / f"seg_{index:03d}.mp4"
        duration = max(0.1, clip.end_seconds - clip.start_seconds)
        _run_ffmpeg(
            [
                "-ss",
                f"{clip.start_seconds:.3f}",
                "-i",
                str(source_video_path),
                "-t",
                f"{duration:.3f}",
                "-vf",
                _scale_filter(),
                "-c:v",
                "libx264",
                "-preset",
                ENCODE_PRESET,
                "-crf",
                ENCODE_CRF,
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-ac",
                "2",
                "-ar",
                "44100",
                "-threads",
                "1",
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
            str(output_path),
        ]
    )


def _mix_original_with_music(video_path: Path, music_path: Path, output_path: Path) -> None:
    """Overlay ducked original audio with looping background music."""
    has_original_audio = has_audio_stream(video_path)

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
