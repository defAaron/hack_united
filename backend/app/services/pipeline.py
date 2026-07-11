"""
Pipeline orchestrator.

Ties together audio analysis -> motion analysis -> fusion/ranking -> composition,
updating job status/progress at each stage. Runs as a FastAPI BackgroundTask for
the hackathon MVP; swap for a Celery/RQ worker (PRD 8 stretch goal) if the app
needs to scale beyond a single process.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.core.job_manager import JobManager
from app.models.schemas import JobStage
from app.services import composer, fusion, motion_analysis
from app.services.audio_analysis import analyze_audio_excitement
from app.services.signal_utils import TimeSeries
from app.storage.local import StorageBackend

OUTPUT_FILENAME = "highlight_reel.mp4"


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


def run_pipeline(job_id: str, job_manager: JobManager, storage: StorageBackend) -> None:
    """Executes the full pipeline for a job. Intended to run in a background task."""
    job = job_manager.get(job_id)
    if job is None or job.source_path is None:
        return

    source_path = Path(job.source_path)

    try:
        duration_seconds = _probe_duration_seconds(source_path)

        job_manager.update(
            job_id, stage=JobStage.ANALYZING_AUDIO, progress=10, message="Analyzing crowd reactions..."
        )
        try:
            audio_series = analyze_audio_excitement(source_path)
        except Exception:
            # No usable audio track - fusion stage will fall back to motion-only.
            audio_series = TimeSeries(timestamps=np.array([]), values=np.array([]))

        job_manager.update(
            job_id, stage=JobStage.ANALYZING_MOTION, progress=35, message="Detecting big plays..."
        )
        motion_series = motion_analysis.analyze_motion_excitement(source_path)

        job_manager.update(
            job_id, stage=JobStage.SELECTING_HIGHLIGHTS, progress=60, message="Selecting the best moments..."
        )
        settings = get_settings()
        clips = fusion.select_highlight_clips(audio_series, motion_series, duration_seconds, settings)
        if not clips:
            raise RuntimeError("No highlight moments were detected in this video")

        job_manager.update(job_id, stage=JobStage.RENDERING, progress=80, message="Editing your reel...")
        output_path = storage.path_for(job_id, OUTPUT_FILENAME)
        rendered_duration = composer.render_highlight_reel(source_path, clips, output_path)

        job_manager.update(
            job_id,
            stage=JobStage.DONE,
            progress=100,
            message="Your highlight reel is ready!",
            result_path=str(output_path),
            duration_seconds=rendered_duration,
            clips=clips,
        )
    except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to the client
        job_manager.update(job_id, stage=JobStage.ERROR, progress=100, error=str(exc))
