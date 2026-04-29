interface CompletionBarProps {
  score: number;
}

export function CompletionBar({ score }: CompletionBarProps) {
  const pct = Math.min(100, Math.max(0, Math.round(score)));
  const color =
    pct >= 80 ? "bg-emerald-500" : pct >= 50 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="relative h-2 w-24 overflow-hidden rounded-full bg-gray-200">
        <div
          className={`absolute inset-y-0 left-0 w-full origin-left rounded-full transition-transform ${color}`}
          style={{ transform: `scaleX(${pct / 100})` }}
        />
      </div>
      <span className="text-xs text-text-secondary tabular-nums">{pct}%</span>
    </div>
  );
}
