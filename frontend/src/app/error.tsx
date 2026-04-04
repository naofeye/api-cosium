"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="rounded-full bg-red-50 p-5">
        <AlertTriangle className="h-10 w-10 text-danger" />
      </div>
      <h1 className="mt-6 text-xl font-bold text-text-primary">Une erreur est survenue</h1>
      <p className="mt-2 max-w-md text-sm text-text-secondary">
        {error.message || "Un probleme inattendu s'est produit. Veuillez reessayer."}
      </p>
      <div className="mt-6 flex gap-3">
        <Button variant="outline" onClick={() => (window.location.href = "/actions")}>
          Retour a l&apos;accueil
        </Button>
        <Button onClick={reset}>Reessayer</Button>
      </div>
    </div>
  );
}
