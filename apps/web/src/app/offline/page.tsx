"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, WifiOff } from "lucide-react";

const FEATURES_OFFLINE_AVAILABLE = [
  "Consulter les fiches client deja chargees",
  "Voir les details des dossiers en cours",
  "Lire les devis et factures emis",
  "Parcourir le journal d'audit recent",
];

const FEATURES_OFFLINE_QUEUED = [
  "Modification client (sera synchronisee au retour)",
  "Mise a jour de dossier",
  "Validation paiement manuel",
  "Notes interactions client",
];

export default function OfflinePage() {
  const [online, setOnline] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const handleOnline = () => {
      setOnline(true);
      // Recharge automatique des qu'online
      setTimeout(() => window.location.reload(), 800);
    };
    setOnline(navigator.onLine);
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-12">
      <div className="mx-auto max-w-2xl">
        <div className="text-center mb-10">
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-amber-50">
            <WifiOff className="h-10 w-10 text-amber-600" aria-hidden="true" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Vous etes hors ligne
          </h1>
          <p className="text-sm text-gray-500 max-w-md mx-auto">
            La connexion internet est indisponible. Certaines actions sont
            mises en file d&apos;attente et seront synchronisees au retour.
          </p>
        </div>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
            <h2 className="text-sm font-semibold text-emerald-900 mb-3">
              Disponible hors ligne
            </h2>
            <ul className="space-y-2">
              {FEATURES_OFFLINE_AVAILABLE.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-2 text-sm text-emerald-900"
                >
                  <CheckCircle2
                    size={16}
                    className="mt-0.5 shrink-0 text-emerald-600"
                    aria-hidden="true"
                  />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 p-5">
            <h2 className="text-sm font-semibold text-blue-900 mb-3">
              File d&apos;attente (Background Sync)
            </h2>
            <ul className="space-y-2">
              {FEATURES_OFFLINE_QUEUED.map((feature) => (
                <li
                  key={feature}
                  className="flex items-start gap-2 text-sm text-blue-900"
                >
                  <span
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500"
                    aria-hidden="true"
                  />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <div className="mt-10 flex flex-col items-center gap-3">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-colors hover:bg-primary-hover"
          >
            <RefreshCw className="h-4 w-4" aria-hidden="true" />
            Tester la connexion
          </button>
          {online && (
            <p className="text-xs text-emerald-700 font-medium">
              Reconnecte ! Rechargement de la page...
            </p>
          )}
        </div>

        <p className="mt-12 text-center text-xs text-gray-400">
          OptiFlow AI fonctionne en mode offline grace au Service Worker.
          Vos donnees seront synchronisees automatiquement au retour de la
          connexion.
        </p>
      </div>
    </main>
  );
}
