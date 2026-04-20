interface LoadingStateProps {
  text?: string;
}

export function LoadingState({ text = "Chargement..." }: LoadingStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="space-y-3 w-full max-w-md">
        <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-full animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-5/6 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200" />
      </div>
      <p className="mt-6 text-sm text-text-secondary">{text}</p>
    </div>
  );
}
