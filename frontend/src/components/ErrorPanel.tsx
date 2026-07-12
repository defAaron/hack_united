interface ErrorPanelProps {
  message: string;
  onReset: () => void;
}

export function ErrorPanel({ message, onReset }: ErrorPanelProps) {
  return (
    <div className="panel-surface w-full max-w-xl rounded-2xl p-8 text-center">
      <p className="mb-4 text-lg font-semibold text-[color:var(--accent)]">Something went wrong</p>
      <p className="mb-6 text-sm text-[color:var(--muted)]">{message}</p>
      <button
        type="button"
        onClick={onReset}
        className="rounded-xl bg-[color:var(--accent)] px-6 py-3 font-semibold text-black transition-colors hover:bg-[color:var(--accent-strong)]"
      >
        Try Again
      </button>
    </div>
  );
}
