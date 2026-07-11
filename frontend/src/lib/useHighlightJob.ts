"use client";

import { useCallback, useRef, useState } from "react";

import { ApiError, getJobResult, getJobStatus, uploadVideo } from "./api";
import type { JobResultResponse, JobStatusResponse } from "./types";

type FlowState = "idle" | "uploading" | "processing" | "done" | "error";

const POLL_INTERVAL_MS = 2000;

export function useHighlightJob() {
  const [state, setState] = useState<FlowState>("idle");
  const [status, setStatus] = useState<JobStatusResponse | null>(null);
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const reset = useCallback(() => {
    stopPolling();
    setState("idle");
    setStatus(null);
    setResult(null);
    setErrorMessage(null);
  }, [stopPolling]);

  const submit = useCallback(
    async (file: File, musicTrackId?: string) => {
      reset();
      setState("uploading");
      try {
        const { job_id } = await uploadVideo(file, musicTrackId);
        setState("processing");

        pollRef.current = setInterval(async () => {
          try {
            const latestStatus = await getJobStatus(job_id);
            setStatus(latestStatus);

            if (latestStatus.stage === "done") {
              stopPolling();
              const jobResult = await getJobResult(job_id);
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
      } catch (err) {
        setErrorMessage(err instanceof ApiError ? err.message : "Upload failed.");
        setState("error");
      }
    },
    [reset, stopPolling]
  );

  return { state, status, result, errorMessage, submit, reset };
}
