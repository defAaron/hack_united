"""
Visual motion excitement analysis (PRD 5.2 step 3 / 6.1).

Samples a low-resolution, low-fps grayscale stream via ffmpeg and computes
frame-to-frame motion scores. Avoids OpenCV decoding full-resolution AV1/H.265
frames (the previous path could take many minutes on ~11 min 1080p uploads).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.services.signal_utils import TimeSeries, normalize

logger = logging.getLogger(__name__)

ANALYSIS_WIDTH = 320
ANALYSIS_HEIGHT = 180


def analyze_motion_excitement(video_path: Path) -> TimeSeries:
    """Compute a 0-1 normalized excitement curve from frame-to-frame motion."""
    settings = get_settings()
    sample_fps = max(1.0, min(settings.motion_sample_fps, 5.0))

    # One ffmpeg decode pass at tiny resolution/fps — much faster than OpenCV
    # walking every full-res frame of an AV1 source.
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps},scale={ANALYSIS_WIDTH}:{ANALYSIS_HEIGHT},format=gray",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "gray",
        "pipe:1",
    ]

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.stdout is not None

    frame_size = ANALYSIS_WIDTH * ANALYSIS_HEIGHT
    timestamps: list[float] = []
    scores: list[float] = []
    prev: np.ndarray | None = None
    frame_index = 0

    try:
        while True:
            raw = process.stdout.read(frame_size)
            if len(raw) < frame_size:
                break

            frame = np.frombuffer(raw, dtype=np.uint8)
            if prev is not None:
                motion_score = float(np.mean(np.abs(frame.astype(np.int16) - prev.astype(np.int16))))
                timestamps.append(frame_index / sample_fps)
                scores.append(motion_score)

            prev = frame
            frame_index += 1
    finally:
        process.stdout.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace") if process.stderr else ""
        return_code = process.wait()

    if return_code not in (0, None) and not timestamps:
        raise RuntimeError(f"Motion analysis ffmpeg failed: {stderr[-1000:]}")

    values = normalize(np.array(scores, dtype=np.float64))
    logger.info("Motion analysis frames=%d sample_fps=%.1f", len(timestamps), sample_fps)
    return TimeSeries(timestamps=np.array(timestamps, dtype=np.float64), values=values)
