"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import {
  RefreshCw,
  ArrowRight,
  CheckCircle,
  Users,
  FileText,
  ShoppingBag,
} from "lucide-react";

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
}

interface SyncCounts {
  customers: number;
  invoices: number;
  products: number;
}

export function StepSynchronisation({ onNext }: { onNext: () => void }) {
  const { data: syncStatus, mutate: mutateSyncStatus } =
    useSWR<SyncStatus>("/sync/status");
  const { toast } = useToast();
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [syncResult, setSyncResult] = useState<SyncCounts | null>(null);

  const isConnected = syncStatus?.authenticated === true;
  const alreadySynced = syncStatus?.first_sync_done === true;

  const handleSync = useCallback(async () => {
    setSyncing(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + Math.random() * 15, 90));
    }, 500);
    try {
      const data = await fetchJson<{ status: string; details: SyncCounts }>(
        "/onboarding/first-sync",
        { method: "POST" }
      );
      setProgress(100);
      setSyncResult(data.details);
      mutateSyncStatus();
      toast("Synchronisation terminee avec succes", "success");
    } catch (err) {
      toast(
        err instanceof Error
          ? err.message
          : "Erreur lors de la synchronisation",
        "error"
      );
    } finally {
      clearInterval(interval);
      setSyncing(false);
    }
  }, [mutateSyncStatus, toast]);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">
          Premiere synchronisation
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Importez vos clients, factures et produits depuis Cosium.
        </p>
      </div>

      {!isConnected && !alreadySynced && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm text-amber-700">
            La connexion Cosium n&apos;est pas encore configuree. Vous pourrez
            synchroniser vos donnees une fois la connexion etablie.
          </p>
        </div>
      )}

      {(isConnected || alreadySynced) && !syncResult && !syncing && (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center">
          <RefreshCw className="mx-auto h-12 w-12 text-blue-400 mb-4" />
          <p className="text-sm text-gray-600 mb-6">
            {alreadySynced
              ? "Une synchronisation a deja ete effectuee. Vous pouvez en relancer une."
              : "Cliquez sur le bouton ci-dessous pour lancer l'importation."}
          </p>
          <Button onClick={handleSync}>Lancer la synchronisation</Button>
        </div>
      )}

      {syncing && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-8 text-center space-y-4">
          <div className="mx-auto mb-2 h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="text-sm font-medium text-blue-700">
            Synchronisation en cours...
          </p>
          <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-blue-500">
            {Math.round(progress)}% — Veuillez patienter
          </p>
        </div>
      )}

      {syncResult && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle className="h-5 w-5 text-emerald-600" />
            <span className="text-sm font-semibold text-emerald-700">
              Synchronisation terminee
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <Users className="mx-auto h-6 w-6 text-blue-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.customers}
              </p>
              <p className="text-xs text-gray-500">Clients</p>
            </div>
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <FileText className="mx-auto h-6 w-6 text-amber-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.invoices}
              </p>
              <p className="text-xs text-gray-500">Factures</p>
            </div>
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <ShoppingBag className="mx-auto h-6 w-6 text-purple-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.products}
              </p>
              <p className="text-xs text-gray-500">Produits</p>
            </div>
          </div>
        </div>
      )}

      <Button onClick={onNext} className="w-full">
        Continuer
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}
