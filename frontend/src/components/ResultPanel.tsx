import { resolveMediaUrl } from "@/lib/api";
import type { JobResultResponse } from "@/lib/types";

interface ResultPanelProps {
  result: JobResultResponse;
  onReset: () => void;
}

export function ResultPanel({ result, onReset }: ResultPanelProps) {
  const videoSrc = resolveMediaUrl(result.video_url);

  return (
    <div className="w-full max-w-2xl text-center">
      <p className="mb-4 text-lg font-semibold text-emerald-300">
        🎉 Your {result.duration_seconds.toFixed(0)}s highlight reel is ready ({result.clip_count} clips)
      </p>

      <video
        src={videoSrc}
        controls
        className="w-full rounded-2xl border border-slate-700 shadow-lg"
      />

      <div className="mt-6 flex justify-center gap-4">
        <a
          href={videoSrc}
          download
          className="rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-slate-950 transition-colors hover:bg-emerald-400"
        >
          Download Reel
        </a>
        <button
          type="button"
          onClick={onReset}
          className="rounded-xl border border-slate-600 px-6 py-3 font-semibold text-slate-200 transition-colors hover:border-slate-400"
        >
          Create Another
        </button>
      </div>
    </div>
  );
}
