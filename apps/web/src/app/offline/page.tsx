"use client";

import { WifiOff, RefreshCw } from "lucide-react";

export default function OfflinePage() {
  return (
    <main className="min-h-screen flex items-center justify-center bg-bg-page px-6">
      <div className="max-w-md text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
          <WifiOff className="h-8 w-8 text-amber-600" aria-hidden="true" />
        </div>
        <h1 className="text-2xl font-bold text-text-primary mb-2">Vous etes hors ligne</h1>
        <p className="text-sm text-text-secondary mb-8">
          Aucune connexion Internet detectee. Certaines fonctionnalites ne sont pas disponibles
          tant que la connexion n&apos;est pas retablie.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-hover"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          Reessayer
        </button>
      </div>
    </main>
  );
}
