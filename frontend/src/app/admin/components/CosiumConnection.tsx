import { KPICard } from "@/components/ui/KPICard";
import { CheckCircle, AlertCircle, Wifi, Calendar, Clock } from "lucide-react";

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
  erp_type?: string;
}

interface CosiumConnectionProps {
  syncStatus: SyncStatus | undefined;
}

export function CosiumConnection({ syncStatus }: CosiumConnectionProps) {
  return (
    <>
      {/* Connexion Cosium */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Wifi className="h-5 w-5" /> Connexion Cosium
        </h3>
        {syncStatus ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KPICard
              icon={syncStatus.configured ? CheckCircle : AlertCircle}
              label="Configuration"
              value={syncStatus.configured ? "Configure" : "Non configure"}
              color={syncStatus.configured ? "success" : "danger"}
            />
            <KPICard
              icon={syncStatus.authenticated ? CheckCircle : AlertCircle}
              label="Authentification"
              value={syncStatus.authenticated ? "Connecte" : "Non connecte"}
              color={syncStatus.authenticated ? "success" : "warning"}
            />
            <KPICard icon={Wifi} label="Tenant" value={syncStatus.tenant || "Non defini"} color="info" />
          </div>
        ) : (
          <p className="text-sm text-text-secondary">Non disponible</p>
        )}
      </div>

      {/* Synchronisation Cosium -- Statut detaille */}
      {syncStatus && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5" /> Synchronisation Cosium
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <KPICard
              icon={syncStatus.first_sync_done ? CheckCircle : AlertCircle}
              label="Premiere synchronisation"
              value={syncStatus.first_sync_done ? "Effectuee" : "Non effectuee"}
              color={syncStatus.first_sync_done ? "success" : "warning"}
            />
            <KPICard
              icon={Clock}
              label="Derniere synchronisation"
              value={
                syncStatus.last_sync_at
                  ? new Intl.DateTimeFormat("fr-FR", {
                      day: "2-digit",
                      month: "short",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(new Date(syncStatus.last_sync_at))
                  : "Jamais"
              }
              color={syncStatus.last_sync_at ? "info" : "warning"}
            />
            <KPICard
              icon={Wifi}
              label="Type ERP"
              value={syncStatus.erp_type || "cosium"}
              color="info"
            />
          </div>
        </div>
      )}
    </>
  );
}
