"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, listMusicTracks, resolveMediaUrl } from "@/lib/api";
import type { MusicTrack } from "@/lib/types";

interface UploadPanelProps {
  onSubmit: (file: File, musicTrackId: string) => void;
}

const ACCEPTED_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo"];

export function UploadPanel({ onSubmit }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [tracks, setTracks] = useState<MusicTrack[]>([]);
  const [selectedTrackId, setSelectedTrackId] = useState<string>("");
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
    <div className="w-full max-w-xl">
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
        className={`flex cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-12 text-center transition-colors ${
          isDragging
            ? "border-emerald-400 bg-emerald-950/30"
            : "border-slate-600 bg-slate-900/40 hover:border-slate-400"
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <span className="text-3xl">🎬</span>
        {selectedFile ? (
          <>
            <p className="font-medium text-slate-100">{selectedFile.name}</p>
            <p className="text-sm text-slate-400">
              {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB — click to choose a different file
            </p>
          </>
        ) : (
          <>
            <p className="font-medium text-slate-100">Drag & drop your game footage</p>
            <p className="text-sm text-slate-400">or click to browse (MP4, MOV, AVI)</p>
          </>
        )}
      </div>

      <div className="mt-6">
        <p className="mb-3 text-sm font-medium text-slate-300">Background music</p>
        {tracksError && <p className="mb-3 text-sm text-red-400">{tracksError}</p>}
        <div className="space-y-2">
          {tracks.map((track) => (
            <label
              key={track.id}
              className={`flex cursor-pointer items-center justify-between rounded-xl border px-4 py-3 transition-colors ${
                selectedTrackId === track.id
                  ? "border-emerald-400 bg-emerald-950/40"
                  : "border-slate-700 bg-slate-900/50 hover:border-slate-500"
              }`}
            >
              <span className="flex items-center gap-3">
                <input
                  type="radio"
                  name="music-track"
                  value={track.id}
                  checked={selectedTrackId === track.id}
                  onChange={() => setSelectedTrackId(track.id)}
                  className="accent-emerald-400"
                />
                <span className="font-medium text-slate-100">{track.title}</span>
              </span>
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  togglePreview(track);
                }}
                className="rounded-lg border border-slate-600 px-3 py-1 text-xs text-slate-300 hover:border-slate-400"
              >
                {previewingId === track.id ? "Stop" : "Preview"}
              </button>
            </label>
          ))}
          {tracks.length === 0 && !tracksError && (
            <p className="text-sm text-slate-500">Loading music tracks...</p>
          )}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Original game audio stays in the reel, mixed under the selected track.
        </p>
      </div>

      <button
        type="button"
        disabled={!selectedFile || !selectedTrackId}
        onClick={() => selectedFile && selectedTrackId && onSubmit(selectedFile, selectedTrackId)}
        className="mt-6 w-full rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        Generate Highlights
      </button>
    </div>
  );
}
