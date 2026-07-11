"""
Visual motion excitement analysis (PRD 5.2 step 3 / 6.1).

Samples video frames at a reduced rate and computes a motion-intensity score
per window using frame differencing as a fast baseline, with an optional
switch to dense optical flow (`calcOpticalFlowFarneback`) for higher fidelity
once performance headroom allows (tracked as a follow-up, see PRD 6.3).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.services.signal_utils import TimeSeries, normalize


def analyze_motion_excitement(video_path: Path) -> TimeSeries:
    """Compute a 0-1 normalized excitement curve from frame-to-frame motion."""
    settings = get_settings()

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video for motion analysis: {video_path}")

    source_fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
    sample_fps = min(settings.motion_sample_fps, source_fps)
    frame_stride = max(1, round(source_fps / sample_fps))

    timestamps: list[float] = []
    scores: list[float] = []

    prev_gray: np.ndarray | None = None
    frame_index = 0

    try:
        while True:
            ok = capture.grab()
            if not ok:
                break

            if frame_index % frame_stride == 0:
                ok, frame = capture.retrieve()
                if not ok:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (320, 180))  # downscale for speed

                if prev_gray is not None:
                    diff = cv2.absdiff(gray, prev_gray)
                    motion_score = float(np.mean(diff))
                    timestamp = frame_index / source_fps
                    timestamps.append(timestamp)
                    scores.append(motion_score)

                prev_gray = gray

            frame_index += 1
    finally:
        capture.release()

    values = normalize(np.array(scores, dtype=np.float64))
    return TimeSeries(timestamps=np.array(timestamps, dtype=np.float64), values=values)
