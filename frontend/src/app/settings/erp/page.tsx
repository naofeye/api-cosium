"use client";

import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Database, Check, Clock, AlertCircle } from "lucide-react";

interface ERPType {
  type: string;
  status: string;
  label: string;
}

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  erp_type: string;
  tenant_name: string;
}

export default function ERPSettingsPage() {
  const { data: erpTypes = [], error: erpError, isLoading: erpLoading, mutate } = useSWR<ERPType[]>("/sync/erp-types");
  const { data: syncStatus, isLoading: syncLoading } = useSWR<SyncStatus>("/sync/status");

  const loading = erpLoading || syncLoading;

  if (loading)
    return (
      <PageLayout title="Configuration ERP">
        <LoadingState text="Chargement..." />
      </PageLayout>
    );
  if (erpError)
    return (
      <PageLayout title="Configuration ERP">
        <ErrorState message={erpError?.message ?? "Erreur"} onRetry={() => mutate()} />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Configuration ERP"
      description="Gerez la connexion a votre logiciel de gestion optique"
      breadcrumb={[{ label: "Parametres" }, { label: "ERP" }]}
    >
      {/* Status actuel */}
      {syncStatus && (
        <div className="mb-8 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Database className="h-5 w-5" /> Connexion actuelle
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <span className="text-sm text-text-secondary">Type d&apos;ERP :</span>
              <span className="font-medium capitalize">{syncStatus.erp_type}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-text-secondary">Statut :</span>
              {syncStatus.configured ? (
                <span className="flex items-center gap-1 text-sm font-medium text-success">
                  <Check className="h-4 w-4" /> Configure
                </span>
              ) : (
                <span className="flex items-center gap-1 text-sm font-medium text-warning">
                  <AlertCircle className="h-4 w-4" /> Non configure
                </span>
              )}
            </div>
            <div className="flex items-center gap-3">
              <span className="text-sm text-text-secondary">Magasin :</span>
              <span className="font-medium">{syncStatus.tenant_name}</span>
            </div>
          </div>
        </div>
      )}

      {/* Liste des ERP */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold mb-4">Logiciels ERP supportes</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {erpTypes.map((erp) => {
            const isActive = syncStatus?.erp_type === erp.type;
            const isSupported = erp.status === "supported";

            return (
              <div
                key={erp.type}
                className={`rounded-xl border-2 p-5 transition-colors ${
                  isActive
                    ? "border-primary bg-blue-50"
                    : isSupported
                      ? "border-border bg-bg-card hover:border-gray-300"
                      : "border-border bg-gray-50 opacity-60"
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-semibold text-lg">{erp.label}</h4>
                  {isActive && (
                    <span className="flex items-center gap-1 text-xs font-medium text-primary bg-blue-100 rounded-full px-2 py-0.5">
                      <Check className="h-3 w-3" /> Actif
                    </span>
                  )}
                  {!isActive && isSupported && (
                    <span className="text-xs font-medium text-success bg-emerald-50 rounded-full px-2 py-0.5">
                      Disponible
                    </span>
                  )}
                  {!isSupported && (
                    <span className="flex items-center gap-1 text-xs font-medium text-text-secondary bg-gray-100 rounded-full px-2 py-0.5">
                      <Clock className="h-3 w-3" /> Bientot
                    </span>
                  )}
                </div>

                {isSupported ? (
                  <p className="text-sm text-text-secondary">
                    {erp.type === "cosium"
                      ? "Connecteur complet vers Cosium (c1.cosium.biz). Synchronisation clients, factures et produits."
                      : `Connecteur vers ${erp.label}. Configuration disponible.`}
                  </p>
                ) : (
                  <p className="text-sm text-text-secondary">
                    D&apos;autres ERP seront bientot supportes. Contactez-nous pour accelerer l&apos;integration de{" "}
                    {erp.label}.
                  </p>
                )}

                {isActive && syncStatus?.configured && (
                  <div className="mt-3">
                    <Button variant="outline" size="sm" onClick={() => (window.location.href = "/getting-started")}>
                      Reconfigurer
                    </Button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </PageLayout>
  );
}
