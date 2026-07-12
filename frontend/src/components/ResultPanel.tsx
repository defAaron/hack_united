import { resolveMediaUrl } from "@/lib/api";
import type { HighlightClip, JobResultResponse } from "@/lib/types";

import { TimelineEditor } from "./TimelineEditor";

interface ResultPanelProps {
  result: JobResultResponse;
  onRerender: (clips: HighlightClip[]) => void;
  onReset: () => void;
}

export function ResultPanel({ result, onRerender, onReset }: ResultPanelProps) {
  const videoSrc = resolveMediaUrl(result.video_url);
  // Bust browser cache after re-render (same URL path, new file contents).
  const cacheBustedSrc = `${videoSrc}?t=${encodeURIComponent(String(result.duration_seconds))}-${result.clip_count}`;

  return (
    <div className="flex w-full max-w-2xl flex-col items-center">
      <div className="panel-surface w-full rounded-2xl p-6 text-center sm:p-8">
        <p className="mb-2 text-lg font-semibold text-[color:var(--accent)]">
          Your {result.duration_seconds.toFixed(0)}s highlight reel is ready ({result.clip_count}{" "}
          clips)
        </p>
        {result.music_track_title && (
          <p className="mb-4 text-sm text-[color:var(--muted)]">
            Soundtrack:{" "}
            <span className="text-[color:var(--accent)]">{result.music_track_title}</span> (mixed
            with original audio)
          </p>
        )}

        <video
          key={cacheBustedSrc}
          src={cacheBustedSrc}
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

      <TimelineEditor
        key={`${result.job_id}-${result.clip_count}-${result.clips.map((c) => c.start_seconds).join(",")}`}
        result={result}
        onRerender={onRerender}
      />
    </div>
  );
}
