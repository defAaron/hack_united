"use client";

import { useMemo, useState } from "react";

import type { HighlightClip, JobResultResponse } from "@/lib/types";
import { formatTimestamp } from "@/lib/types";

const NUDGE_SECONDS = 2;
const MIN_CLIP_LENGTH = 0.5;

type EditableClip = HighlightClip & { id: string; kept: boolean };

interface TimelineEditorProps {
  result: JobResultResponse;
  isBusy?: boolean;
  onRerender: (clips: HighlightClip[]) => void;
}

function ensureId(clip: HighlightClip, index: number): string {
  return clip.id ?? `clip-${index}-${clip.start_seconds.toFixed(2)}`;
}

export function TimelineEditor({ result, isBusy = false, onRerender }: TimelineEditorProps) {
  const sourceDuration = Math.max(result.source_duration_seconds ?? 0, 1);

  const [clips, setClips] = useState<EditableClip[]>(() =>
    result.clips.map((clip, index) => ({
      ...clip,
      id: ensureId(clip, index),
      kept: true,
    }))
  );

  const keptClips = useMemo(() => clips.filter((clip) => clip.kept), [clips]);
  const estimatedDuration = keptClips.reduce(
    (sum, clip) => sum + (clip.end_seconds - clip.start_seconds),
    0
  );
  const dirty =
    keptClips.length !== result.clips.length ||
    keptClips.some((clip, index) => {
      const original = result.clips[index];
      if (!original) return true;
      return (
        clip.id !== ensureId(original, index) ||
        Math.abs(clip.start_seconds - original.start_seconds) > 0.01 ||
        Math.abs(clip.end_seconds - original.end_seconds) > 0.01
      );
    }) ||
    // Also dirty if order changed relative to original ids
    keptClips.map((c) => c.id).join("|") !==
      result.clips.map((c, i) => ensureId(c, i)).join("|");

  const updateClip = (id: string, updater: (clip: EditableClip) => EditableClip) => {
    setClips((prev) => prev.map((clip) => (clip.id === id ? updater(clip) : clip)));
  };

  const nudge = (id: string, delta: number) => {
    updateClip(id, (clip) => {
      const length = clip.end_seconds - clip.start_seconds;
      let start = clip.start_seconds + delta;
      let end = clip.end_seconds + delta;
      if (start < 0) {
        end -= start;
        start = 0;
      }
      if (end > sourceDuration) {
        const overflow = end - sourceDuration;
        start = Math.max(0, start - overflow);
        end = sourceDuration;
      }
      if (end - start < MIN_CLIP_LENGTH) {
        return clip;
      }
      // Preserve intended length when possible
      if (Math.abs(end - start - length) > 0.01 && start === 0) {
        end = Math.min(sourceDuration, start + length);
      }
      return { ...clip, start_seconds: start, end_seconds: end };
    });
  };

  const move = (id: string, direction: -1 | 1) => {
    setClips((prev) => {
      const index = prev.findIndex((clip) => clip.id === id);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= prev.length) return prev;
      const next = [...prev];
      const [item] = next.splice(index, 1);
      next.splice(target, 0, item);
      return next;
    });
  };

  const handleRerender = () => {
    if (keptClips.length === 0) return;
    onRerender(
      keptClips.map(({ id, start_seconds, end_seconds, excitement_score }) => ({
        id,
        start_seconds,
        end_seconds,
        excitement_score,
      }))
    );
  };

  return (
    <div className="panel-surface mt-4 w-full max-w-2xl rounded-2xl p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[color:var(--accent)]">Timeline editor</h2>
          <p className="text-sm text-[color:var(--muted)]">
            Keep, drop, reorder, or nudge clips ±{NUDGE_SECONDS}s, then re-render.
          </p>
        </div>
        <p className="text-sm text-[color:var(--muted)]">
          {keptClips.length} kept · ~{estimatedDuration.toFixed(0)}s
        </p>
      </div>

      {/* Scrubbable-looking source timeline with clip blocks */}
      <div className="mb-5">
        <div className="mb-1 flex justify-between text-[11px] text-[color:var(--muted)]">
          <span>0:00</span>
          <span>{formatTimestamp(sourceDuration)}</span>
        </div>
        <div className="relative h-10 overflow-hidden rounded-xl border border-[color:var(--panel-border)] bg-black/45">
          {keptClips.map((clip, index) => {
            const left = (clip.start_seconds / sourceDuration) * 100;
            const width = ((clip.end_seconds - clip.start_seconds) / sourceDuration) * 100;
            return (
              <div
                key={clip.id}
                title={`Clip ${index + 1}: ${formatTimestamp(clip.start_seconds)}–${formatTimestamp(clip.end_seconds)}`}
                className="absolute top-1 bottom-1 rounded-md border border-[rgba(243,229,171,0.45)] bg-[rgba(243,229,171,0.28)]"
                style={{ left: `${left}%`, width: `${Math.max(width, 0.8)}%` }}
              />
            );
          })}
        </div>
      </div>

      <ul className="space-y-3">
        {clips.map((clip, index) => {
          const length = clip.end_seconds - clip.start_seconds;
          return (
            <li
              key={clip.id}
              className={`rounded-xl border px-4 py-3 transition-opacity ${
                clip.kept
                  ? "border-[color:var(--panel-border)] bg-black/25"
                  : "border-[color:var(--panel-border)] bg-black/10 opacity-45"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium text-[color:var(--accent)]">
                    Clip {index + 1}
                    <span className="ml-2 text-sm font-normal text-[color:var(--muted)]">
                      {formatTimestamp(clip.start_seconds)} – {formatTimestamp(clip.end_seconds)} (
                      {length.toFixed(1)}s)
                    </span>
                  </p>
                  <p className="text-xs text-[color:var(--muted)]">
                    Score {(clip.excitement_score * 100).toFixed(0)}%
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => updateClip(clip.id, (c) => ({ ...c, kept: !c.kept }))}
                    className="rounded-lg border border-[color:var(--panel-border)] px-2.5 py-1 text-xs text-[color:var(--accent)] hover:border-[rgba(243,229,171,0.45)] disabled:opacity-40"
                  >
                    {clip.kept ? "Drop" : "Keep"}
                  </button>
                  <button
                    type="button"
                    disabled={isBusy || index === 0}
                    onClick={() => move(clip.id, -1)}
                    className="rounded-lg border border-[color:var(--panel-border)] px-2.5 py-1 text-xs text-[color:var(--accent)] hover:border-[rgba(243,229,171,0.45)] disabled:opacity-40"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    disabled={isBusy || index === clips.length - 1}
                    onClick={() => move(clip.id, 1)}
                    className="rounded-lg border border-[color:var(--panel-border)] px-2.5 py-1 text-xs text-[color:var(--accent)] hover:border-[rgba(243,229,171,0.45)] disabled:opacity-40"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    disabled={isBusy || !clip.kept}
                    onClick={() => nudge(clip.id, -NUDGE_SECONDS)}
                    className="rounded-lg border border-[color:var(--panel-border)] px-2.5 py-1 text-xs text-[color:var(--accent)] hover:border-[rgba(243,229,171,0.45)] disabled:opacity-40"
                  >
                    −{NUDGE_SECONDS}s
                  </button>
                  <button
                    type="button"
                    disabled={isBusy || !clip.kept}
                    onClick={() => nudge(clip.id, NUDGE_SECONDS)}
                    className="rounded-lg border border-[color:var(--panel-border)] px-2.5 py-1 text-xs text-[color:var(--accent)] hover:border-[rgba(243,229,171,0.45)] disabled:opacity-40"
                  >
                    +{NUDGE_SECONDS}s
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>

      <button
        type="button"
        disabled={isBusy || keptClips.length === 0 || !dirty}
        onClick={handleRerender}
        className="mt-5 w-full rounded-xl bg-[color:var(--accent)] px-6 py-3 font-semibold text-black transition-colors hover:bg-[color:var(--accent-strong)] disabled:cursor-not-allowed disabled:bg-[#3a3420] disabled:text-[#7a7048]"
      >
        {isBusy ? "Re-rendering..." : "Re-render highlight reel"}
      </button>
    </div>
  );
}
