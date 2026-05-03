"use client";

import { useEffect } from "react";

import * as Sentry from "@sentry/nextjs";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/Button";

function humanMessage(error: Error & { status?: number }): string {
  const status = error.status;
  if (status != null) {
    if (status >= 500) return "Le serveur rencontre un probleme. Merci de reessayer dans quelques minutes.";
    if (status === 403) return "Vous n'avez pas les droits necessaires pour cette action.";
    if (status === 404) return "L'element demande est introuvable ou a ete supprime.";
    if (status === 408 || status === 504) return "Le serveur met trop de temps a repondre. Verifiez votre connexion.";
    if (status === 429) return "Trop de requetes en peu de temps. Patientez quelques secondes.";
    if (status >= 400) return "La requete n'a pas pu aboutir. Verifiez les donnees et reessayez.";
  }
  if (error.name === "TypeError" && /fetch|network/i.test(error.message)) {
    return "Connexion impossible au serveur. Verifiez votre reseau.";
  }
  return "Un probleme inattendu s'est produit. Reessayez, et si l'erreur persiste contactez le support.";
}

export default function GlobalError({ error, reset }: { error: Error & { digest?: string; status?: number }; reset: () => void }) {
  useEffect(() => {
    // Best-effort capture Sentry. Si Sentry n'est pas configure (dev),
    // l'init est en mode `enabled: false`, donc no-op.
    Sentry.captureException(error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center">
      <div className="rounded-full bg-red-50 p-5">
        <AlertTriangle className="h-10 w-10 text-danger" />
      </div>
      <h1 className="mt-6 text-xl font-bold text-text-primary">Une erreur est survenue</h1>
      <p className="mt-2 max-w-md text-sm text-text-secondary">{humanMessage(error)}</p>
      {error.digest && (
        <p className="mt-1 text-xs text-text-secondary opacity-60">Reference : {error.digest}</p>
      )}
      <div className="mt-6 flex gap-3">
        <Button variant="outline" onClick={() => (window.location.href = "/actions")}>
          Retour à l&apos;accueil
        </Button>
        <Button onClick={reset}>Réessayer</Button>
      </div>
    </div>
  );
}
