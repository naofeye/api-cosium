"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export function ErrorState({ message = "Une erreur est survenue. Veuillez réessayer.", onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-red-50 p-4">
        <AlertTriangle className="h-8 w-8 text-danger" aria-hidden="true" />
      </div>
      <p className="mt-4 max-w-sm text-sm text-text-secondary">{message}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="mt-4">
          Réessayer
        </Button>
      )}
    </div>
  );
}
