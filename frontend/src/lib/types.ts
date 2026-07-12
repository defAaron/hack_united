/**
 * Mirrors the backend Pydantic schemas in `backend/app/models/schemas.py`.
 * Keep these in sync manually for the hackathon; consider generating this
 * file from the FastAPI OpenAPI spec later if the contract grows.
 */

export type JobStage =
  | "queued"
  | "analyzing_audio"
  | "analyzing_motion"
  | "selecting_highlights"
  | "rendering"
  | "done"
  | "error";

export interface UploadResponse {
  job_id: string;
}

export interface JobStatusResponse {
  job_id: string;
  stage: JobStage;
  progress: number;
  message?: string | null;
  error?: string | null;
}

export interface HighlightClip {
  id?: string | null;
  start_seconds: number;
  end_seconds: number;
  excitement_score: number;
}

export interface MusicTrack {
  id: string;
  title: string;
  preview_url: string;
}

export interface JobResultResponse {
  job_id: string;
  video_url: string;
  thumbnail_url?: string | null;
  duration_seconds: number;
  source_duration_seconds?: number;
  clip_count: number;
  clips: HighlightClip[];
  music_track_id?: string | null;
  music_track_title?: string | null;
}

export const STAGE_LABELS: Record<JobStage, string> = {
  queued: "Queued...",
  analyzing_audio: "Analyzing crowd reactions...",
  analyzing_motion: "Detecting big plays...",
  selecting_highlights: "Selecting the best moments...",
  rendering: "Editing your reel...",
  done: "Your highlight reel is ready!",
  error: "Something went wrong.",
};

/** Allowed highlight reel lengths (seconds) — keep in sync with backend pipeline_options. */
export const REEL_LENGTH_OPTIONS = [30, 60, 90] as const;
export type ReelLengthSeconds = (typeof REEL_LENGTH_OPTIONS)[number];
export const DEFAULT_REEL_LENGTH: ReelLengthSeconds = 90;

export function formatTimestamp(seconds: number): string {
  const clamped = Math.max(0, seconds);
  const mins = Math.floor(clamped / 60);
  const secs = Math.floor(clamped % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
