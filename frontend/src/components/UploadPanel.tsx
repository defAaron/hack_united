"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, listMusicTracks, resolveMediaUrl } from "@/lib/api";
import {
  DEFAULT_REEL_LENGTH,
  REEL_LENGTH_OPTIONS,
  type MusicTrack,
  type ReelLengthSeconds,
} from "@/lib/types";

interface UploadPanelProps {
  onSubmit: (
    file: File,
    options: { musicTrackId: string; targetDurationSeconds: ReelLengthSeconds }
  ) => void;
}

const ACCEPTED_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo"];

export function UploadPanel({ onSubmit }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tracks, setTracks] = useState<MusicTrack[]>([]);
  const [selectedTrackId, setSelectedTrackId] = useState<string>("");
  const [reelLength, setReelLength] = useState<ReelLengthSeconds>(DEFAULT_REEL_LENGTH);
  const [tracksError, setTracksError] = useState<string | null>(null);
  const [previewingId, setPreviewingId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMusicTracks()
      .then((loaded) => {
        if (cancelled) return;
        setTracks(loaded);
        if (loaded.length > 0) {
          setSelectedTrackId(loaded[0].id);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setTracksError(err instanceof ApiError ? err.message : "Could not load music tracks.");
      });
    return () => {
      cancelled = true;
      audioRef.current?.pause();
    };
  }, []);

  const handleFile = useCallback((file: File | undefined) => {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert("Please upload an MP4, MOV, or AVI file.");
      return;
    }
    setSelectedFile(file);
  }, []);

  const togglePreview = useCallback(
    (track: MusicTrack) => {
      if (previewingId === track.id) {
        audioRef.current?.pause();
        setPreviewingId(null);
        return;
      }

      audioRef.current?.pause();
      const audio = new Audio(resolveMediaUrl(track.preview_url));
      audioRef.current = audio;
      setPreviewingId(track.id);
      audio.play().catch(() => setPreviewingId(null));
      audio.onended = () => setPreviewingId(null);
    },
    [previewingId]
  );

  return (
    <div className="panel-surface w-full max-w-xl rounded-2xl p-6 sm:p-8">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files?.[0]);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border border-dashed p-12 text-center transition-colors ${
          isDragging
            ? "border-[color:var(--accent)] bg-[rgba(243,229,171,0.08)]"
            : "border-[color:var(--panel-border)] hover:border-[rgba(243,229,171,0.4)]"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        {selectedFile ? (
          <>
            <p className="font-medium text-[color:var(--accent)]">{selectedFile.name}</p>
            <p className="text-sm text-[color:var(--muted)]">
              {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB — click to choose a different file
            </p>
          </>
        ) : (
          <>
            <p className="font-medium text-[color:var(--accent)]">Drag & drop your game footage</p>
            <p className="text-sm text-[color:var(--muted)]">or click to browse (MP4, MOV, AVI)</p>
          </>
        )}
      </div>

      <div className="mt-6">
        <p className="mb-3 text-sm font-medium text-[color:var(--accent)]">Reel length</p>
        <div className="grid grid-cols-3 gap-2">
          {REEL_LENGTH_OPTIONS.map((seconds) => (
            <button
              key={seconds}
              type="button"
              onClick={() => setReelLength(seconds)}
              className={`rounded-xl border px-3 py-2.5 text-sm font-medium transition-colors ${
                reelLength === seconds
                  ? "border-[color:var(--accent)] bg-[rgba(243,229,171,0.12)] text-[color:var(--accent)]"
                  : "border-[color:var(--panel-border)] text-[color:var(--muted)] hover:border-[rgba(243,229,171,0.35)]"
              }`}
            >
              {seconds}s
            </button>
          ))}
        </div>
        <p className="mt-2 text-xs text-[color:var(--muted)]">
          Target length for the auto-selected highlight package.
        </p>
      </div>

      <div className="mt-6">
        <p className="mb-3 text-sm font-medium text-[color:var(--accent)]">Background music</p>
        {tracksError && <p className="mb-3 text-sm text-red-300">{tracksError}</p>}
        <div className="space-y-2">
          {tracks.map((track) => (
            <label
              key={track.id}
              className={`flex cursor-pointer items-center justify-between rounded-xl border px-4 py-3 transition-colors ${
                selectedTrackId === track.id
                  ? "border-[color:var(--accent)] bg-[rgba(243,229,171,0.1)]"
                  : "border-[color:var(--panel-border)] hover:border-[rgba(243,229,171,0.35)]"
              }`}
            >
              <span className="flex items-center gap-3">
                <input
                  type="radio"
                  name="music-track"
                  value={track.id}
                  checked={selectedTrackId === track.id}
                  onChange={() => setSelectedTrackId(track.id)}
                  className="accent-[#f3e5ab]"
                />
                <span className="font-medium text-[color:var(--accent)]">{track.title}</span>
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  togglePreview(track);
                }}
                className="rounded-lg border border-[color:var(--panel-border)] px-3 py-1 text-xs text-[color:var(--muted)] hover:border-[rgba(243,229,171,0.45)] hover:text-[color:var(--accent)]"
              >
                {previewingId === track.id ? "Stop" : "Preview"}
              </button>
            </label>
          ))}
          {tracks.length === 0 && !tracksError && (
            <p className="text-sm text-[color:var(--muted)]">Loading music tracks...</p>
          )}
        </div>
        <p className="mt-2 text-xs text-[color:var(--muted)]">
          Original game audio stays in the reel, mixed under the selected track.
        </p>
      </div>

      <button
        type="button"
        disabled={!selectedFile || !selectedTrackId}
        onClick={() =>
          selectedFile &&
          selectedTrackId &&
          onSubmit(selectedFile, {
            musicTrackId: selectedTrackId,
            targetDurationSeconds: reelLength,
          })
        }
        className="mt-6 w-full rounded-xl bg-[color:var(--accent)] px-6 py-3 font-semibold text-black transition-colors hover:bg-[color:var(--accent-strong)] disabled:cursor-not-allowed disabled:bg-[#3a3420] disabled:text-[#7a7048]"
      >
        Generate Highlights
      </button>
    </div>
  );
}
