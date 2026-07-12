"""
Shared Pydantic models / enums used across the API layer and pipeline services.

Keeping these in one place makes it easy to keep the frontend TypeScript types
(see frontend/src/lib/api.ts) in sync with the backend contract.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class JobStage(str, Enum):
    QUEUED = "queued"
    ANALYZING_AUDIO = "analyzing_audio"
    ANALYZING_MOTION = "analyzing_motion"
    SELECTING_HIGHLIGHTS = "selecting_highlights"
    RENDERING = "rendering"
    DONE = "done"
    ERROR = "error"


class UploadResponse(BaseModel):
    job_id: str


class JobStatusResponse(BaseModel):
    job_id: str
    stage: JobStage
    progress: int = Field(ge=0, le=100)
    message: str | None = None
    error: str | None = None


class HighlightClip(BaseModel):
    """A single selected highlight segment, in source-video time."""

    id: str | None = None
    start_seconds: float
    end_seconds: float
    excitement_score: float


class MusicTrackResponse(BaseModel):
    id: str
    title: str
    preview_url: str


class JobResultResponse(BaseModel):
    job_id: str
    video_url: str
    thumbnail_url: str | None = None
    duration_seconds: float
    source_duration_seconds: float = 0.0
    clip_count: int
    clips: list[HighlightClip] = Field(default_factory=list)
    music_track_id: str | None = None
    music_track_title: str | None = None


class RerenderRequest(BaseModel):
    """User-edited clip list from the timeline editor."""

    clips: list[HighlightClip] = Field(min_length=1)


class PipelineOptions(BaseModel):
    """Optional per-job overrides for the highlight-detection algorithm (PRD 6.3)."""

    target_duration_seconds: float | None = None
    audio_weight: float | None = None
    motion_weight: float | None = None
    music_track_id: str | None = None
