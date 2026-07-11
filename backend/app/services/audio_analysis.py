"""
Audio excitement analysis (PRD 5.2 step 2 / 6.1).

Extracts the audio track from the source video and computes a smoothed,
normalized excitement score over time based on short-time energy (RMS).

This module currently ships a working implementation using ffmpeg + librosa.
Tuning (window size, smoothing, peak thresholding) happens in `fusion.py`,
which consumes the raw time series produced here.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.services.signal_utils import TimeSeries, normalize


def _extract_audio_wav(video_path: Path) -> Path:
    """Extract mono 22.05kHz audio track to a temp WAV file via ffmpeg."""
    tmp_wav = Path(tempfile.mkstemp(suffix=".wav")[1])
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(tmp_wav),
        ],
        check=True,
        capture_output=True,
    )
    return tmp_wav


def analyze_audio_excitement(video_path: Path) -> TimeSeries:
    """Compute a 0-1 normalized excitement curve from audio energy.

    Raises:
        RuntimeError: if the video has no usable audio track. Callers should
            catch this and fall back to motion-only scoring (PRD 6.4).
    """
    import librosa  # local import: heavy dependency, only needed here

    settings = get_settings()
    wav_path = _extract_audio_wav(video_path)
    try:
        y, sr = librosa.load(str(wav_path), sr=None, mono=True)
        if y.size == 0:
            raise RuntimeError("Extracted audio track is empty")

        window_samples = max(1, int(settings.analysis_window_seconds * sr))
        hop_samples = window_samples

        rms = librosa.feature.rms(y=y, frame_length=window_samples, hop_length=hop_samples)[0]
        timestamps = librosa.frames_to_time(
            np.arange(len(rms)), sr=sr, hop_length=hop_samples
        )

        values = normalize(rms)
        return TimeSeries(timestamps=timestamps, values=values)
    finally:
        wav_path.unlink(missing_ok=True)


def has_sufficient_variance(series: TimeSeries, min_std: float = 0.05) -> bool:
    """Used by the fusion stage to decide whether to trust the audio signal (PRD 6.4)."""
    if series.values.size == 0:
        return False
    return float(np.std(series.values)) >= min_std
