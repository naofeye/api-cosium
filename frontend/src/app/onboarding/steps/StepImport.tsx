"use client";

import { useState, useTransition } from "react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { Download, CheckCircle, Users, FileText, ShoppingBag } from "lucide-react";
import type { FirstSyncResponse, SyncDetail } from "../helpers";

export function StepImport({ onComplete, onSkip }: { onComplete: () => void; onSkip: () => void }) {
  const { toast } = useToast();
  const [syncPending, startSyncTransition] = useTransition();
  const [syncResult, setSyncResult] = useState<SyncDetail | null>(null);
  const [apiError, setApiError] = useState("");

  const handleSync = () => {
    setApiError("");
    startSyncTransition(async () => {
      try {
        const data = await fetchJson<FirstSyncResponse>("/onboarding/first-sync", { method: "POST" });
        setSyncResult(data.details);
        toast("Importation terminee avec succès", "success");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Erreur lors de l'importation";
        setApiError(msg);
        toast(msg, "error");
      }
    });
  };

  return (
    <div className="space-y-5">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-gray-900">Importer vos donnees</h2>
        <p className="mt-1 text-sm text-gray-500">
          Importez vos clients, factures et produits depuis Cosium en un clic.
        </p>
      </div>
      {!syncResult && !syncPending && (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center">
          <Download className="mx-auto h-12 w-12 text-blue-400 mb-4" />
          <p className="text-sm text-gray-600 mb-6">L&apos;importation va recuperer vos donnees depuis Cosium.</p>
          <Button type="button" onClick={handleSync} className="mx-auto">
            Lancer l&apos;importation
          </Button>
        </div>
      )}
      {syncPending && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-8 text-center">
          <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="text-sm font-medium text-blue-700">Importation en cours...</p>
          <p className="mt-1 text-xs text-blue-500">Veuillez patienter.</p>
        </div>
      )}
      {syncResult && (
        <div className="space-y-4">
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="h-5 w-5 text-emerald-600" />
              <span className="text-sm font-semibold text-emerald-700">Importation terminee</span>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="rounded-lg bg-white p-4 text-center shadow-sm">
                <Users className="mx-auto h-6 w-6 text-blue-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{syncResult.customers}</p>
                <p className="text-xs text-gray-500">Clients</p>
              </div>
              <div className="rounded-lg bg-white p-4 text-center shadow-sm">
                <FileText className="mx-auto h-6 w-6 text-amber-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{syncResult.invoices}</p>
                <p className="text-xs text-gray-500">Factures</p>
              </div>
              <div className="rounded-lg bg-white p-4 text-center shadow-sm">
                <ShoppingBag className="mx-auto h-6 w-6 text-purple-500 mb-1" />
                <p className="text-2xl font-bold text-gray-900">{syncResult.products}</p>
                <p className="text-xs text-gray-500">Produits</p>
              </div>
            </div>
          </div>
          <Button type="button" onClick={onComplete} className="w-full">
            Continuer
          </Button>
        </div>
      )}
      {apiError && !syncPending && (
        <div className="space-y-3">
          <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{apiError}</div>
          <Button type="button" onClick={handleSync} className="w-full">
            Réessayer
          </Button>
        </div>
      )}
      {!syncResult && !syncPending && (
        <Button type="button" variant="ghost" onClick={onSkip} className="w-full">
          Passer cette étape
        </Button>
      )}
    </div>
  );
}
