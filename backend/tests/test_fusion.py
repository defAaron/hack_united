import numpy as np

from app.core.config import Settings
from app.services.fusion import compute_excitement_curve, select_highlight_clips
from app.services.signal_utils import TimeSeries


def _make_series(peaks_at: list[float], length_seconds: float = 60.0, step: float = 0.5) -> TimeSeries:
    timestamps = np.arange(0.0, length_seconds, step)
    values = np.zeros_like(timestamps)
    for peak in peaks_at:
        idx = int(peak / step)
        if 0 <= idx < len(values):
            values[idx] = 1.0
    return TimeSeries(timestamps=timestamps, values=values)


def test_compute_excitement_curve_combines_audio_and_motion() -> None:
    audio = _make_series([10.0])
    motion = _make_series([10.0])
    settings = Settings(audio_weight=0.6, motion_weight=0.4)

    curve = compute_excitement_curve(audio, motion, settings)

    peak_idx = int(np.argmax(curve.values))
    assert abs(curve.timestamps[peak_idx] - 10.0) < 1.0
    assert curve.values[peak_idx] > 0.9


def test_select_highlight_clips_respects_min_gap_and_duration_budget() -> None:
    audio = _make_series([5.0, 6.0, 20.0, 40.0])  # 5.0 and 6.0 are too close together
    motion = _make_series([5.0, 6.0, 20.0, 40.0])
    settings = Settings(
        min_gap_between_clips_seconds=8.0,
        clip_pre_roll_seconds=2.0,
        clip_post_roll_seconds=2.0,
        target_duration_seconds=90.0,
    )

    clips = select_highlight_clips(audio, motion, video_duration_seconds=60.0, settings=settings)

    starts = [round(clip.start_seconds, 1) for clip in clips]
    assert len(clips) <= 3  # 5.0/6.0 collapse into a single accepted peak due to min gap
    assert starts == sorted(starts)  # chronological order preserved
