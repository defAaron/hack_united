import type {
  HighlightClip,
  JobResultResponse,
  JobStatusResponse,
  MusicTrack,
  UploadResponse,
} from "./types";

/**
 * Base URL of the FastAPI backend. Configure via NEXT_PUBLIC_API_URL:
 * - Local dev: defaults to http://localhost:8000 (see .env.local.example)
 * - Vercel:    point this at your hosted backend (Railway/Fly/Render), since
 *              the media-processing pipeline (ffmpeg) is not a good
 *              fit for Vercel's serverless Python runtime.
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(body.detail ?? response.statusText, response.status);
  }
  return response.json() as Promise<T>;
}

export async function listMusicTracks(): Promise<MusicTrack[]> {
  const response = await fetch(`${API_BASE_URL}/api/music`);
  return handleResponse<MusicTrack[]>(response);
}

export async function uploadVideo(
  file: File,
  options?: { musicTrackId?: string; targetDurationSeconds?: number }
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (options?.musicTrackId) {
    formData.append("music_track_id", options.musicTrackId);
  }
  if (options?.targetDurationSeconds != null) {
    formData.append("target_duration_seconds", String(options.targetDurationSeconds));
  }

  const response = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<UploadResponse>(response);
}

export async function getJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/api/status/${jobId}`);
  return handleResponse<JobStatusResponse>(response);
}

export async function getJobResult(jobId: string): Promise<JobResultResponse> {
  const response = await fetch(`${API_BASE_URL}/api/result/${jobId}`);
  return handleResponse<JobResultResponse>(response);
}

export async function rerenderJob(jobId: string, clips: HighlightClip[]): Promise<UploadResponse> {
  const response = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/rerender`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ clips }),
  });
  return handleResponse<UploadResponse>(response);
}

export function resolveMediaUrl(path: string): string {
  return path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
}

export { ApiError, API_BASE_URL };
