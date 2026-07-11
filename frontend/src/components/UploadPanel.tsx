"use client";

import { useCallback, useRef, useState } from "react";

interface UploadPanelProps {
  onFileSelected: (file: File) => void;
}

const ACCEPTED_TYPES = ["video/mp4", "video/quicktime", "video/x-msvideo"];

export function UploadPanel({ onFileSelected }: UploadPanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File | undefined) => {
    if (!file) return;
    if (!ACCEPTED_TYPES.includes(file.type)) {
      alert("Please upload an MP4, MOV, or AVI file.");
      return;
    }
    setSelectedFile(file);
  }, []);

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

      <button
        type="button"
        disabled={!selectedFile}
        onClick={() => selectedFile && onFileSelected(selectedFile)}
        className="mt-6 w-full rounded-xl bg-emerald-500 px-6 py-3 font-semibold text-slate-950 transition-colors hover:bg-emerald-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      >
        Generate Highlights
      </button>
    </div>
  );
}
