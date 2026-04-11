export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/3 mb-3"></div>
      <div className="h-8 bg-gray-200 rounded w-2/3"></div>
    </div>
  );
}
