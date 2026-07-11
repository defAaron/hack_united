interface ErrorPanelProps {
  message: string;
  onReset: () => void;
}

export function ErrorPanel({ message, onReset }: ErrorPanelProps) {
  return (
    <div className="w-full max-w-xl text-center">
      <p className="mb-4 text-lg font-semibold text-red-400">Something went wrong</p>
      <p className="mb-6 text-sm text-slate-400">{message}</p>
      <button
        type="button"
        onClick={onReset}
        className="rounded-xl bg-slate-800 px-6 py-3 font-semibold text-slate-200 transition-colors hover:bg-slate-700"
      >
        Try Again
      </button>
    </div>
  );
}
