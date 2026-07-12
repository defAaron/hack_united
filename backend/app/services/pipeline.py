"""
Pipeline orchestrator.

Ties together audio analysis -> motion analysis -> fusion/ranking -> composition,
updating job status/progress at each stage. Runs as a FastAPI BackgroundTask for
the hackathon MVP.
"""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.core.job_manager import JobManager
from app.models.schemas import HighlightClip, JobStage
from app.services import composer, fusion, motion_analysis
from app.services.audio_analysis import analyze_audio_excitement
from app.services.media_utils import probe_duration_seconds
from app.services.music_catalog import get_music_track, resolve_music_path
from app.services.signal_utils import TimeSeries
from app.storage.local import StorageBackend

OUTPUT_FILENAME = "highlight_reel.mp4"
logger = logging.getLogger(__name__)


def run_pipeline(job_id: str, job_manager: JobManager, storage: StorageBackend) -> None:
    """Executes the full pipeline for a job. Intended to run in a background task."""
    job = job_manager.get(job_id)
    if job is None or job.source_path is None:
        return

    source_path = Path(job.source_path)
    started = time.perf_counter()

    try:
        duration_seconds = probe_duration_seconds(source_path)
        job_manager.update(job_id, source_duration_seconds=duration_seconds)
        logger.info("Job %s started duration=%.1fs path=%s", job_id, duration_seconds, source_path)

        job_manager.update(
            job_id, stage=JobStage.ANALYZING_AUDIO, progress=10, message="Analyzing crowd reactions..."
        )
        stage_started = time.perf_counter()
        try:
            audio_series = analyze_audio_excitement(source_path)
        except Exception:
            # No usable audio track - fusion stage will fall back to motion-only.
            audio_series = TimeSeries(timestamps=np.array([]), values=np.array([]))
        logger.info("Job %s audio analysis took %.1fs", job_id, time.perf_counter() - stage_started)

        job_manager.update(
            job_id, stage=JobStage.ANALYZING_MOTION, progress=35, message="Detecting big plays..."
        )
        stage_started = time.perf_counter()
        motion_series = motion_analysis.analyze_motion_excitement(source_path)
        logger.info("Job %s motion analysis took %.1fs", job_id, time.perf_counter() - stage_started)

        job_manager.update(
            job_id, stage=JobStage.SELECTING_HIGHLIGHTS, progress=60, message="Selecting the best moments..."
        )
        settings = get_settings()
        if job.target_duration_seconds is not None:
            settings = settings.model_copy(
                update={"target_duration_seconds": float(job.target_duration_seconds)}
            )
        clips = fusion.select_highlight_clips(audio_series, motion_series, duration_seconds, settings)
        if not clips:
            raise RuntimeError("No highlight moments were detected in this video")
        logger.info(
            "Job %s selected %d clips (target=%.0fs)",
            job_id,
            len(clips),
            settings.target_duration_seconds,
        )

        music_track = get_music_track(job.music_track_id)
        music_path = resolve_music_path(job.music_track_id)
        music_title = music_track.title if music_track else None
        music_id = music_track.id if music_track else None

        job_manager.update(
            job_id,
            stage=JobStage.RENDERING,
            progress=80,
            message=f"Editing your reel{f' with {music_title}' if music_title else ''}...",
        )
        stage_started = time.perf_counter()
        output_path = storage.path_for(job_id, OUTPUT_FILENAME)
        rendered_duration = composer.render_highlight_reel(
            source_path, clips, output_path, music_track_path=music_path
        )
        logger.info("Job %s render took %.1fs", job_id, time.perf_counter() - stage_started)

        job_manager.update(
            job_id,
            stage=JobStage.DONE,
            progress=100,
            message="Your highlight reel is ready!",
            result_path=str(output_path),
            duration_seconds=rendered_duration,
            clips=clips,
            music_track_id=music_id,
            music_track_title=music_title,
        )
        logger.info("Job %s completed in %.1fs", job_id, time.perf_counter() - started)
    except Exception as exc:  # noqa: BLE001 - surface any pipeline failure to the client
        logger.exception("Job %s failed after %.1fs", job_id, time.perf_counter() - started)
        job_manager.update(job_id, stage=JobStage.ERROR, progress=100, error=str(exc))


def run_rerender(
    job_id: str,
    clips: list[HighlightClip],
    job_manager: JobManager,
    storage: StorageBackend,
) -> None:
    """Re-compose the highlight reel from an edited clip list (timeline editor).

    Skips analysis/fusion — only cuts + mixes using the existing source upload
    and soundtrack selection. Safe to call repeatedly on the same job.
    """
    job = job_manager.get(job_id)
    if job is None or job.source_path is None:
        return

    source_path = Path(job.source_path)
    started = time.perf_counter()

    try:
        if not clips:
            raise RuntimeError("At least one clip is required to re-render")

        normalized: list[HighlightClip] = []
        source_duration = job.source_duration_seconds or probe_duration_seconds(source_path)
        for clip in clips:
            start = max(0.0, float(clip.start_seconds))
            end = min(source_duration, float(clip.end_seconds))
            if end - start < 0.5:
                continue
            normalized.append(
                HighlightClip(
                    id=clip.id or str(uuid.uuid4()),
                    start_seconds=start,
                    end_seconds=end,
                    excitement_score=float(clip.excitement_score),
                )
            )
        if not normalized:
            raise RuntimeError("No valid clips remaining after edit")

        music_path = resolve_music_path(job.music_track_id)
        music_track = get_music_track(job.music_track_id)

        job_manager.update(
            job_id,
            stage=JobStage.RENDERING,
            progress=80,
            message="Re-editing your reel...",
            error=None,
        )
        output_path = storage.path_for(job_id, OUTPUT_FILENAME)
        rendered_duration = composer.render_highlight_reel(
            source_path, normalized, output_path, music_track_path=music_path
        )
        job_manager.update(
            job_id,
            stage=JobStage.DONE,
            progress=100,
            message="Your highlight reel is ready!",
            result_path=str(output_path),
            duration_seconds=rendered_duration,
            clips=normalized,
            music_track_id=music_track.id if music_track else job.music_track_id,
            music_track_title=music_track.title if music_track else job.music_track_title,
            source_duration_seconds=source_duration,
        )
        logger.info(
            "Job %s re-render completed in %.1fs (%d clips)",
            job_id,
            time.perf_counter() - started,
            len(normalized),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Job %s re-render failed after %.1fs", job_id, time.perf_counter() - started)
        job_manager.update(job_id, stage=JobStage.ERROR, progress=100, error=str(exc))
