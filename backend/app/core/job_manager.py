"""
In-memory job state store.

This is intentionally isolated behind a small interface (`JobManager`) so it can
be swapped for a Redis-backed implementation later (needed once we move to a
real task queue like Celery/RQ, or deploy multiple backend instances) without
touching the route handlers.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field

from app.models.schemas import HighlightClip, JobStage


@dataclass
class Job:
    id: str
    stage: JobStage = JobStage.QUEUED
    progress: int = 0
    message: str | None = None
    error: str | None = None

    source_path: str | None = None
    result_path: str | None = None
    thumbnail_path: str | None = None
    duration_seconds: float = 0.0
    source_duration_seconds: float = 0.0
    clips: list[HighlightClip] = field(default_factory=list)
    music_track_id: str | None = None
    music_track_title: str | None = None
    # Per-job override for fusion target reel length (30/60/90). None = settings default.
    target_duration_seconds: float | None = None


class JobManager:
    """Thread-safe in-memory job registry.

    NOTE: this does not persist across process restarts and does not scale
    across multiple backend workers. Swap for a Redis/DB-backed implementation
    before running the pipeline as a distributed task queue (see PRD 8, Celery+Redis
    stretch goal).
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create_job(self) -> Job:
        job = Job(id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **fields) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            for key, value in fields.items():
                setattr(job, key, value)
            return job


_job_manager: JobManager | None = None


def get_job_manager() -> JobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
