"""
Event fusion & ranking (PRD 5.2 step 4 / 6.1-6.4).

Combines the audio and motion excitement curves into a single weighted score,
finds local maxima with a minimum spacing, expands each into a clip window,
and greedily selects clips (in descending score order) until the target reel
duration is filled - then re-sorts the selection chronologically.
"""

from __future__ import annotations

import numpy as np

from app.core.config import Settings, get_settings
from app.models.schemas import HighlightClip
from app.services.audio_analysis import has_sufficient_variance
from app.services.signal_utils import TimeSeries


def _resample_to_common_grid(
    audio: TimeSeries, motion: TimeSeries, window_seconds: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Interpolate both series onto a shared timestamp grid."""
    end_time = max(
        audio.timestamps[-1] if audio.timestamps.size else 0.0,
        motion.timestamps[-1] if motion.timestamps.size else 0.0,
    )
    grid = np.arange(0.0, end_time, window_seconds)
    if grid.size == 0:
        return grid, np.zeros(0), np.zeros(0)

    audio_on_grid = (
        np.interp(grid, audio.timestamps, audio.values) if audio.timestamps.size else np.zeros_like(grid)
    )
    motion_on_grid = (
        np.interp(grid, motion.timestamps, motion.values) if motion.timestamps.size else np.zeros_like(grid)
    )
    return grid, audio_on_grid, motion_on_grid


def compute_excitement_curve(
    audio: TimeSeries, motion: TimeSeries, settings: Settings | None = None
) -> TimeSeries:
    """Fuse audio + motion signals into a single weighted excitement curve.

    Falls back to motion-only weighting if the audio signal is too flat to be
    meaningful (e.g. silent gym footage) - see PRD 6.4.
    """
    settings = settings or get_settings()
    grid, audio_on_grid, motion_on_grid = _resample_to_common_grid(
        audio, motion, settings.analysis_window_seconds
    )
    if grid.size == 0:
        return TimeSeries(timestamps=grid, values=np.zeros(0))

    audio_weight, motion_weight = settings.audio_weight, settings.motion_weight
    if not has_sufficient_variance(audio):
        audio_weight, motion_weight = 0.0, 1.0

    fused = audio_weight * audio_on_grid + motion_weight * motion_on_grid
    return TimeSeries(timestamps=grid, values=fused)


def _find_local_maxima(curve: TimeSeries, min_gap_seconds: float) -> list[tuple[float, float]]:
    """Return (timestamp, score) pairs for peaks, enforcing a minimum spacing.

    Greedy approach: sort all points by score descending, accept a point only
    if it is not within `min_gap_seconds` of an already-accepted point.
    """
    if curve.timestamps.size == 0:
        return []

    order = np.argsort(curve.values)[::-1]
    accepted: list[tuple[float, float]] = []

    for idx in order:
        t, score = float(curve.timestamps[idx]), float(curve.values[idx])
        if score <= 0:
            continue
        if all(abs(t - accepted_t) >= min_gap_seconds for accepted_t, _ in accepted):
            accepted.append((t, score))

    return accepted


def select_highlight_clips(
    audio: TimeSeries, motion: TimeSeries, video_duration_seconds: float, settings: Settings | None = None
) -> list[HighlightClip]:
    """End-to-end fusion -> peak detection -> clip windowing -> duration-budgeted selection."""
    settings = settings or get_settings()
    curve = compute_excitement_curve(audio, motion, settings)
    peaks = _find_local_maxima(curve, settings.min_gap_between_clips_seconds)

    candidates: list[HighlightClip] = []
    for timestamp, score in peaks:
        start = max(0.0, timestamp - settings.clip_pre_roll_seconds)
        end = min(video_duration_seconds, timestamp + settings.clip_post_roll_seconds)
        if end - start <= 0.5:
            continue
        candidates.append(HighlightClip(start_seconds=start, end_seconds=end, excitement_score=score))

    # Greedily fill the target duration budget, highest score first.
    candidates.sort(key=lambda clip: clip.excitement_score, reverse=True)
    selected: list[HighlightClip] = []
    total_duration = 0.0
    for clip in candidates:
        clip_len = clip.end_seconds - clip.start_seconds
        if total_duration + clip_len > settings.target_duration_seconds and selected:
            continue
        selected.append(clip)
        total_duration += clip_len
        if total_duration >= settings.target_duration_seconds:
            break

    # Chronological order for a natural narrative flow in the final edit.
    selected.sort(key=lambda clip: clip.start_seconds)
    return selected
