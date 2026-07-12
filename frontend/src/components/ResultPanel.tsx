import { resolveMediaUrl } from "@/lib/api";
import type { JobResultResponse } from "@/lib/types";

interface ResultPanelProps {
  result: JobResultResponse;
  onReset: () => void;
}

export function ResultPanel({ result, onReset }: ResultPanelProps) {
  const videoSrc = resolveMediaUrl(result.video_url);

  return (
    <div className="panel-surface w-full max-w-2xl rounded-2xl p-6 text-center sm:p-8">
      <p className="mb-2 text-lg font-semibold text-[color:var(--accent)]">
        Your {result.duration_seconds.toFixed(0)}s highlight reel is ready ({result.clip_count} clips)
      </p>
      {result.music_track_title && (
        <p className="mb-4 text-sm text-[color:var(--muted)]">
          Soundtrack:{" "}
          <span className="text-[color:var(--accent)]">{result.music_track_title}</span> (mixed with
          original audio)
        </p>
      )}

      <video
        src={videoSrc}
        controls
        className="w-full rounded-2xl border border-[color:var(--panel-border)] shadow-lg"
      />

      <div className="mt-6 flex justify-center gap-4">
        <a
          href={videoSrc}
          download
          className="rounded-xl bg-[color:var(--accent)] px-6 py-3 font-semibold text-black transition-colors hover:bg-[color:var(--accent-strong)]"
        >
          Download Reel
        </a>
        <button
          type="button"
          onClick={onReset}
          className="rounded-xl border border-[color:var(--panel-border)] px-6 py-3 font-semibold text-[color:var(--accent)] transition-colors hover:border-[rgba(243,229,171,0.45)]"
        >
          Create Another
        </button>
      </div>
    </div>
  );
}
