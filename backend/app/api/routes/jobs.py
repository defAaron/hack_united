"""
Job lifecycle routes: upload -> status -> result.

Kept as a single router for the hackathon MVP; split into upload.py/status.py/
result.py modules if this file grows unwieldy as more endpoints are added.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.core.job_manager import JobManager, get_job_manager
from app.core.pipeline_options import ALLOWED_TARGET_DURATIONS, DEFAULT_TARGET_DURATION
from app.models.schemas import (
    JobResultResponse,
    JobStage,
    JobStatusResponse,
    RerenderRequest,
    UploadResponse,
)
from app.services.music_catalog import get_music_track, list_music_tracks
from app.services.pipeline import OUTPUT_FILENAME, run_pipeline, run_rerender
from app.storage.local import StorageBackend, get_storage_backend

router = APIRouter(prefix="/api", tags=["jobs"])
logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "application/octet-stream",  # some browsers omit a precise video MIME type
}


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    music_track_id: str | None = Form(default=None),
    target_duration_seconds: int | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    job_manager: JobManager = Depends(get_job_manager),
    storage: StorageBackend = Depends(get_storage_backend),
) -> UploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    available_ids = {track.id for track in list_music_tracks()}
    if music_track_id and music_track_id not in available_ids:
        raise HTTPException(status_code=400, detail=f"Unknown music track: {music_track_id}")

    selected_track = get_music_track(music_track_id) if music_track_id else None
    if selected_track is None and available_ids:
        # Default to the first catalog track when the client omits a selection.
        selected_track = list_music_tracks()[0]

    resolved_duration = (
        target_duration_seconds if target_duration_seconds is not None else DEFAULT_TARGET_DURATION
    )
    if resolved_duration not in ALLOWED_TARGET_DURATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"target_duration_seconds must be one of {list(ALLOWED_TARGET_DURATIONS)}",
        )

    # Stream to disk instead of buffering the whole file in RAM (176MB+ uploads).
    job = job_manager.create_job()
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    destination = storage.path_for(job.id, f"source{suffix}")
    destination.parent.mkdir(parents=True, exist_ok=True)

    bytes_written = 0
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    with destination.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            bytes_written += len(chunk)
            if bytes_written > max_bytes:
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max is {settings.max_upload_size_mb}MB.",
                )
            out.write(chunk)

    job_manager.update(
        job.id,
        source_path=str(destination),
        stage=JobStage.QUEUED,
        progress=0,
        music_track_id=selected_track.id if selected_track else None,
        music_track_title=selected_track.title if selected_track else None,
        target_duration_seconds=float(resolved_duration),
    )
    logger.info(
        "Job %s uploaded %.1fMB music=%s target=%ss — starting pipeline thread",
        job.id,
        bytes_written / (1024 * 1024),
        selected_track.id if selected_track else "none",
        resolved_duration,
    )

    # Dedicated daemon thread (not FastAPI BackgroundTasks) so long AV1 jobs
    # keep running independently of the request lifecycle / reload shutdown.
    thread = threading.Thread(
        target=run_pipeline,
        args=(job.id, job_manager, storage),
        name=f"pipeline-{job.id[:8]}",
        daemon=True,
    )
    thread.start()

    return UploadResponse(job_id=job.id)


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str, job_manager: JobManager = Depends(get_job_manager)
) -> JobStatusResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobStatusResponse(
        job_id=job.id, stage=job.stage, progress=job.progress, message=job.message, error=job.error
    )


@router.get("/result/{job_id}", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    job_manager: JobManager = Depends(get_job_manager),
    storage: StorageBackend = Depends(get_storage_backend),
) -> JobResultResponse:
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.stage != JobStage.DONE:
        raise HTTPException(status_code=409, detail=f"Job is not finished yet (stage={job.stage})")

    return JobResultResponse(
        job_id=job.id,
        video_url=storage.url_for(job.id, OUTPUT_FILENAME),
        thumbnail_url=None,
        duration_seconds=job.duration_seconds,
        source_duration_seconds=job.source_duration_seconds,
        clip_count=len(job.clips),
        clips=job.clips,
        music_track_id=job.music_track_id,
        music_track_title=job.music_track_title,
    )


@router.post("/jobs/{job_id}/rerender", response_model=UploadResponse)
async def rerender_job(
    job_id: str,
    body: RerenderRequest,
    job_manager: JobManager = Depends(get_job_manager),
    storage: StorageBackend = Depends(get_storage_backend),
) -> UploadResponse:
    """Re-render a finished job from a user-edited clip timeline."""
    job = job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.source_path is None:
        raise HTTPException(status_code=409, detail="Job has no source video to re-render")
    if job.stage not in {JobStage.DONE, JobStage.ERROR}:
        raise HTTPException(
            status_code=409,
            detail=f"Job cannot be re-rendered while stage={job.stage}",
        )
    if not body.clips:
        raise HTTPException(status_code=400, detail="At least one clip is required")

    job_manager.update(
        job_id,
        stage=JobStage.QUEUED,
        progress=0,
        message="Queued for re-edit...",
        error=None,
        clips=list(body.clips),
    )

    thread = threading.Thread(
        target=run_rerender,
        args=(job_id, list(body.clips), job_manager, storage),
        name=f"rerender-{job_id[:8]}",
        daemon=True,
    )
    thread.start()
    logger.info("Job %s re-render queued with %d clips", job_id, len(body.clips))
    return UploadResponse(job_id=job_id)
