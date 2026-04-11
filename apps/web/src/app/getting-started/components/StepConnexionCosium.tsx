"use client";

import useSWR from "swr";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Link2, CheckCircle, XCircle, ArrowRight } from "lucide-react";

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
}

export function StepConnexionCosium({ onNext }: { onNext: () => void }) {
  const { data: syncStatus } = useSWR<SyncStatus>("/sync/status");
  const isConnected = syncStatus?.authenticated === true;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">
          Connecter votre Cosium
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          OptiFlow se synchronise avec votre ERP Cosium pour importer vos
          donnees automatiquement.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 space-y-4">
        <div className="flex items-center gap-3">
          {isConnected ? (
            <CheckCircle className="h-6 w-6 text-emerald-500 shrink-0" />
          ) : (
            <XCircle className="h-6 w-6 text-amber-500 shrink-0" />
          )}
          <div>
            <p className="font-medium text-gray-900">
              {isConnected
                ? "Cosium est connecte"
                : "Cosium n'est pas encore connecte"}
            </p>
            <p className="text-sm text-gray-500">
              {isConnected
                ? `Tenant : ${syncStatus?.tenant_name || syncStatus?.tenant || "Connecte"}`
                : "Rendez-vous dans l'administration pour configurer la connexion."}
            </p>
          </div>
        </div>

        {!isConnected && (
          <Link href="/admin">
            <Button variant="outline" className="w-full">
              <Link2 className="h-4 w-4 mr-2" />
              Configurer la connexion Cosium
            </Button>
          </Link>
        )}
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4 space-y-2">
        <p className="text-sm text-blue-700">
          <strong>Ou trouver vos identifiants Cosium ?</strong> Connectez-vous a votre interface Cosium,
          allez dans <em>Administration &gt; API</em> pour obtenir votre tenant et vos identifiants.
          Vous pouvez aussi utiliser les cookies de session depuis les DevTools du navigateur.
        </p>
        <p className="text-sm text-blue-600">
          <strong>Astuce :</strong> Vous pouvez configurer cela plus tard depuis la page Administration.
        </p>
      </div>

      <Button onClick={onNext} className="w-full">
        Continuer
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}
