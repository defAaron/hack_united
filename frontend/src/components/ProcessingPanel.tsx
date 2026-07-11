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
    <div className="w-full max-w-xl text-center">
      <p className="mb-4 text-lg font-medium text-slate-100">{label}</p>

      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className="h-full rounded-full bg-emerald-500 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <ol className="mt-8 flex flex-wrap justify-center gap-2 text-xs text-slate-500">
        {STAGE_ORDER.slice(0, -1).map((stage, index) => (
          <li
            key={stage}
            className={`rounded-full px-3 py-1 ${
              index <= currentIndex ? "bg-emerald-500/20 text-emerald-300" : "bg-slate-800/60"
            }`}
          >
            {STAGE_LABELS[stage]}
          </li>
        ))}
      </ol>
    </div>
  );
}
