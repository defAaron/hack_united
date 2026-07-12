import { STAGE_LABELS, type JobStatusResponse } from "@/lib/types";

interface ProcessingPanelProps {
  status: JobStatusResponse | null;
}

const STAGE_ORDER = [
  "queued",
  "analyzing_audio",
  "analyzing_motion",
  "selecting_highlights",
  "rendering",
  "done",
] as const;

export function ProcessingPanel({ status }: ProcessingPanelProps) {
  const progress = status?.progress ?? 5;
  const label = status ? STAGE_LABELS[status.stage] : "Uploading your footage...";
  const currentIndex = status ? STAGE_ORDER.indexOf(status.stage as (typeof STAGE_ORDER)[number]) : -1;

  return (
    <div className="panel-surface w-full max-w-xl rounded-2xl p-8 text-center">
      <p className="mb-4 text-lg font-medium text-[color:var(--accent)]">{label}</p>

      <div className="h-2.5 w-full overflow-hidden rounded-full bg-black/50">
        <div
          className="h-full rounded-full bg-[color:var(--accent)] transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <ol className="mt-8 flex flex-wrap justify-center gap-2 text-xs text-[color:var(--muted)]">
        {STAGE_ORDER.slice(0, -1).map((stage, index) => (
          <li
            key={stage}
            className={`rounded-full px-3 py-1 ${
              index <= currentIndex
                ? "bg-[rgba(243,229,171,0.16)] text-[color:var(--accent)]"
                : "bg-black/35"
            }`}
          >
            {STAGE_LABELS[stage]}
          </li>
        ))}
      </ol>
    </div>
  );
}
