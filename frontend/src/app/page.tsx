"use client";

import dynamic from "next/dynamic";

import { ErrorPanel } from "@/components/ErrorPanel";
import { ProcessingPanel } from "@/components/ProcessingPanel";
import { ResultPanel } from "@/components/ResultPanel";
import { UploadPanel } from "@/components/UploadPanel";
import { useHighlightJob } from "@/lib/useHighlightJob";

const Strands = dynamic(() => import("@/components/Strands"), { ssr: false });

export default function Home() {
  const { state, status, result, errorMessage, submit, rerender, reset } = useHighlightJob();

  return (
    <main className="landing-shell">
      <div className="landing-strands">
        <Strands
          colors={["#F3E5AB", "#E8C547", "#B8860B", "#FFF8DC"]}
          count={3}
          speed={0.35}
          amplitude={1}
          waviness={1}
          thickness={0.55}
          glow={2.2}
          taper={3}
          spread={1.1}
          intensity={0.45}
          saturation={1.2}
          opacity={0.85}
          scale={1.35}
          glass={false}
        />
      </div>
      <div className="landing-vignette" />

      <div className="landing-content flex min-h-screen flex-col items-center justify-center gap-10 px-6 py-16">
        <header className="text-center">
          <h1 className="display-title text-5xl sm:text-6xl md:text-7xl">ClipCoach</h1>
          <p className="mx-auto mt-4 max-w-md text-base leading-relaxed text-[color:var(--muted)] sm:text-lg">
            Upload your game tape. Get a highlight reel back in minutes — no editor, no timeline,
            no skills needed.
          </p>
        </header>

        {state === "idle" && <UploadPanel onSubmit={submit} />}
        {(state === "uploading" || state === "processing") && <ProcessingPanel status={status} />}
        {state === "done" && result && (
          <ResultPanel result={result} onRerender={rerender} onReset={reset} />
        )}
        {state === "error" && (
          <ErrorPanel message={errorMessage ?? "Unknown error"} onReset={reset} />
        )}
      </div>
    </main>
  );
}
