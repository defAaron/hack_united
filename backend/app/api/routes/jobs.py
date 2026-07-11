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
from app.models.schemas import JobResultResponse, JobStage, JobStatusResponse, UploadResponse
from app.services.music_catalog import get_music_track, list_music_tracks
from app.services.pipeline import OUTPUT_FILENAME, run_pipeline
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
    )
    logger.info(
        "Job %s uploaded %.1fMB music=%s — starting pipeline thread",
        job.id,
        bytes_written / (1024 * 1024),
        selected_track.id if selected_track else "none",
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
        clip_count=len(job.clips),
        clips=job.clips,
        music_track_id=job.music_track_id,
        music_track_title=job.music_track_title,
    )
