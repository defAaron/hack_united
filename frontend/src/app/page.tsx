"use client";

import { ErrorPanel } from "@/components/ErrorPanel";
import { ProcessingPanel } from "@/components/ProcessingPanel";
import { ResultPanel } from "@/components/ResultPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { useHighlightJob } from "@/lib/useHighlightJob";

export default function Home() {
  const { state, status, result, errorMessage, submit, reset } = useHighlightJob();

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-10 bg-slate-950 px-6 py-16 text-slate-100">
      <header className="text-center">
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
          Clip<span className="text-emerald-400">Coach</span>
        </h1>
        <p className="mt-3 max-w-md text-slate-400">
          Upload your game tape. Get a highlight reel back in minutes — no editor, no timeline,
          no skills needed.
        </p>
      </header>

      {state === "idle" && <UploadPanel onFileSelected={submit} />}
      {(state === "uploading" || state === "processing") && <ProcessingPanel status={status} />}
      {state === "done" && result && <ResultPanel result={result} onReset={reset} />}
      {state === "error" && <ErrorPanel message={errorMessage ?? "Unknown error"} onReset={reset} />}
    </main>
  );
}
