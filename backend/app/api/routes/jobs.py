"""
Job lifecycle routes: upload -> status -> result.

Kept as a single router for the hackathon MVP; split into upload.py/status.py/
result.py modules if this file grows unwieldy as more endpoints are added.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile

from app.core.config import Settings, get_settings
from app.core.job_manager import JobManager, get_job_manager
from app.models.schemas import JobResultResponse, JobStage, JobStatusResponse, UploadResponse
from app.services.pipeline import OUTPUT_FILENAME, run_pipeline
from app.storage.local import StorageBackend, get_storage_backend

router = APIRouter(prefix="/api", tags=["jobs"])

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo"}


@router.post("/upload", response_model=UploadResponse)
async def upload_video(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
    job_manager: JobManager = Depends(get_job_manager),
    storage: StorageBackend = Depends(get_storage_backend),
) -> UploadResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Max is {settings.max_upload_size_mb}MB.",
        )

    job = job_manager.create_job()
    suffix = Path(file.filename or "upload.mp4").suffix or ".mp4"
    saved_path = storage.save_upload(job.id, f"source{suffix}", contents)
    job_manager.update(job.id, source_path=str(saved_path), stage=JobStage.QUEUED, progress=0)

    background_tasks.add_task(run_pipeline, job.id, job_manager, storage)

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
    )
