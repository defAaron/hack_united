"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, getJobResult, getJobStatus, rerenderJob, uploadVideo } from "./api";
import type { HighlightClip, JobResultResponse, JobStatusResponse } from "./types";

type FlowState = "idle" | "uploading" | "processing" | "done" | "error";

const POLL_INTERVAL_MS = 2000;

export function useHighlightJob() {
  const [state, setState] = useState<FlowState>("idle");
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const pollUntilSettled = useCallback(
    (activeJobId: string) => {
      stopPolling();
      pollRef.current = setInterval(async () => {
        try {
          const latestStatus = await getJobStatus(activeJobId);
          setStatus(latestStatus);

          if (latestStatus.stage === "done") {
            stopPolling();
            const jobResult = await getJobResult(activeJobId);
            setResult(jobResult);
            setState("done");
          } else if (latestStatus.stage === "error") {
            stopPolling();
            setErrorMessage(latestStatus.error ?? "Processing failed.");
            setState("error");
          }
        } catch (err) {
          stopPolling();
          setErrorMessage(err instanceof ApiError ? err.message : "Lost connection to server.");
          setState("error");
        }
      }, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setState("idle");
    setStatus(null);
    setResult(null);
    setErrorMessage(null);
    setJobId(null);
  }, [stopPolling]);

  const submit = useCallback(
    async (
      file: File,
      options?: { musicTrackId?: string; targetDurationSeconds?: number }
    ) => {
      reset();
      setState("uploading");
      try {
        const { job_id } = await uploadVideo(file, options);
        setJobId(job_id);
        setState("processing");
        pollUntilSettled(job_id);
      } catch (err) {
        setErrorMessage(err instanceof ApiError ? err.message : "Upload failed.");
        setState("error");
      }
    },
    [pollUntilSettled, reset]
  );

  const rerender = useCallback(
    async (clips: HighlightClip[]) => {
      if (!jobId) {
        setErrorMessage("Missing job id for re-render.");
        setState("error");
        return;
      }
      setState("processing");
      setStatus({
        job_id: jobId,
        stage: "rendering",
        progress: 80,
        message: "Re-editing your reel...",
      });
      try {
        await rerenderJob(jobId, clips);
        pollUntilSettled(jobId);
      } catch (err) {
        setErrorMessage(err instanceof ApiError ? err.message : "Re-render failed.");
        setState("error");
      }
    },
    [jobId, pollUntilSettled]
  );

  return { state, status, result, errorMessage, jobId, submit, rerender, reset };
}
