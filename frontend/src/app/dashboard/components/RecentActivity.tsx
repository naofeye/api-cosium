"use client";

import useSWR from "swr";
import { Activity, User, FileText, CreditCard, FolderOpen, Settings, RefreshCw } from "lucide-react";

interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  created_at: string;
  user_email: string | null;
}

const ENTITY_ICONS: Record<string, typeof Activity> = {
  case: FolderOpen,
  document: FileText,
  payment: CreditCard,
  customer: User,
  user: User,
  settings: Settings,
};

const ACTION_LABELS: Record<string, string> = {
  create: "a cree",
  update: "a modifie",
  delete: "a supprime",
  sync: "a synchronise",
  upload: "a televerse",
  extract: "a extrait",
  login: "s'est connecte",
  export: "a exporte",
};

const ENTITY_LABELS: Record<string, string> = {
  case: "un dossier",
  cases: "les dossiers",
  document: "un document",
  payment: "un paiement",
  customer: "un client",
  customers: "les clients",
  user: "un utilisateur",
  invoice: "une facture",
  devis: "un devis",
  pec_request: "une PEC",
  settings: "les parametres",
};

function formatTimeAgo(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diffSec = Math.floor((now - then) / 1000);

  if (diffSec < 10) return "A l'instant";
  if (diffSec < 60) return `Il y a ${diffSec}s`;

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `Il y a ${diffMin} min`;

  const diffHours = Math.floor(diffMin / 60);
  if (diffHours < 24) return `Il y a ${diffHours}h`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "Hier";
  return `Il y a ${diffDays}j`;
}

function formatUserName(email: string | null): string {
  if (!email) return "Systeme";
  const local = email.split("@")[0];
  return local.charAt(0).toUpperCase() + local.slice(1);
}

export function RecentActivity() {
  const { data, error, isLoading } = useSWR<AuditLogEntry[]>(
    "/audit-logs/recent?limit=5",
    { refreshInterval: 30000 },
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Derniere activite
          </h3>
        </div>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="h-8 w-8 rounded-full bg-gray-200" />
              <div className="flex-1 space-y-1">
                <div className="h-3 bg-gray-200 rounded w-3/4" />
                <div className="h-2 bg-gray-200 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Derniere activite
          </h3>
        </div>
        <p className="text-sm text-text-secondary">Impossible de charger l&apos;activite recente.</p>
      </div>
    );
  }

  const entries = data ?? [];

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Derniere activite
        </h3>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-text-secondary">Aucune activite recente.</p>
      ) : (
        <div className="space-y-3">
          {entries.map((entry) => {
            const Icon = ENTITY_ICONS[entry.entity_type] ?? Activity;
            const actionLabel = ACTION_LABELS[entry.action] ?? entry.action;
            const entityLabel = ENTITY_LABELS[entry.entity_type] ?? entry.entity_type;
            const userName = formatUserName(entry.user_email);

            return (
              <div key={entry.id} className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-100">
                  <Icon className="h-4 w-4 text-text-secondary" aria-hidden="true" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary">
                    <span className="font-medium">{userName}</span>{" "}
                    {actionLabel}{" "}
                    {entityLabel}
                    {entry.entity_id ? ` #${entry.entity_id}` : ""}
                  </p>
                  <p className="text-xs text-text-secondary">{formatTimeAgo(entry.created_at)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
