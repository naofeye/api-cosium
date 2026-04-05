"use client";

import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { Users, FileText, Activity, FolderOpen } from "lucide-react";
import { ActivityChart } from "./components/ActivityChart";
import { HealthStatus } from "./components/HealthStatus";
import { CosiumConnection } from "./components/CosiumConnection";
import { CosiumCookies } from "./components/CosiumCookies";
import { ManualSync } from "./components/ManualSync";
import { RecentActivity } from "./components/RecentActivity";

interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
}

interface HealthData {
  status: string;
  services: Record<string, { status: string; response_ms?: number; error?: string }>;
}

interface MetricsData {
  totals: { users: number; clients: number; dossiers: number; factures: number; paiements: number };
  activity: { actions_last_hour: number; active_users_last_hour: number };
}

export default function AdminPage() {
  const { data: syncStatus, isLoading: syncLoading } = useSWR<SyncStatus>("/sync/status", {
    onError: (err: Error) => {
      console.error("[Admin] Erreur chargement statut sync:", err.message);
    },
  });
  const { data: health, isLoading: healthLoading } = useSWR<HealthData>("/admin/health", {
    onError: (err: Error) => {
      console.error("[Admin] Erreur chargement sante services:", err.message);
    },
  });
  const { data: metrics, isLoading: metricsLoading } = useSWR<MetricsData>("/admin/metrics", {
    onError: (err: Error) => {
      console.error("[Admin] Erreur chargement metriques:", err.message);
    },
  });
  const { data: activity } = useSWR<AuditLogEntry[]>("/audit-logs/recent", {
    refreshInterval: 10000,
    onError: (err: Error) => {
      console.error("[Admin] Erreur chargement activite recente:", err.message);
    },
  });

  const loading = syncLoading || healthLoading || metricsLoading;

  if (loading)
    return (
      <PageLayout title="Chargement...">
        <LoadingState text="Chargement de l'administration..." />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Administration"
      description="Monitoring, synchronisation et parametres"
      breadcrumb={[{ label: "Admin" }]}
    >
      <HealthStatus health={health} />

      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-6">
          <KPICard icon={Users} label="Utilisateurs" value={metrics.totals.users} color="info" />
          <KPICard icon={Users} label="Clients" value={metrics.totals.clients} color="primary" />
          <KPICard icon={FolderOpen} label="Dossiers" value={metrics.totals.dossiers} color="primary" />
          <KPICard icon={FileText} label="Factures" value={metrics.totals.factures} color="info" />
          <KPICard icon={Activity} label="Actions (1h)" value={metrics.activity.actions_last_hour} color="success" />
          <KPICard icon={Users} label="Actifs (1h)" value={metrics.activity.active_users_last_hour} color="success" />
        </div>
      )}

      <CosiumConnection syncStatus={syncStatus} />
      <CosiumCookies />
      <ManualSync />

      {activity && <ActivityChart activity={activity} />}
      <RecentActivity activity={activity} />
    </PageLayout>
  );
}
