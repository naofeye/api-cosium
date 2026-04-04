export default function Loading() {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="space-y-3 w-full max-w-lg px-8">
        <div className="h-6 w-1/3 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-gray-100 mt-2" />
        <div className="mt-6 grid grid-cols-3 gap-4">
          <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
          <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
          <div className="h-24 animate-pulse rounded-xl bg-gray-100" />
        </div>
        <div className="mt-6 h-48 animate-pulse rounded-xl bg-gray-100" />
      </div>
      <p className="mt-8 text-sm text-text-secondary">Chargement...</p>
    </div>
  );
}
