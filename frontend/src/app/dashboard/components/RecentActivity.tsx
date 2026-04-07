"use client";

import useSWR from "swr";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Activity,
  User,
  FileText,
  CreditCard,
  FolderOpen,
  Settings,
  RefreshCw,
  ShieldCheck,
  Receipt,
  ChevronRight,
} from "lucide-react";

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
  client: User,
  user: User,
  settings: Settings,
  sync_customers: RefreshCw,
  sync_invoices: RefreshCw,
  sync: RefreshCw,
  devis: Receipt,
  facture: Receipt,
  pec_request: ShieldCheck,
  invoice: Receipt,
};

const ENTITY_COLORS: Record<string, string> = {
  case: "bg-blue-100 text-blue-600",
  document: "bg-purple-100 text-purple-600",
  payment: "bg-emerald-100 text-emerald-600",
  customer: "bg-amber-100 text-amber-600",
  client: "bg-amber-100 text-amber-600",
  user: "bg-gray-100 text-gray-600",
  settings: "bg-gray-100 text-gray-600",
  sync_customers: "bg-sky-100 text-sky-600",
  sync_invoices: "bg-sky-100 text-sky-600",
  sync: "bg-sky-100 text-sky-600",
  devis: "bg-indigo-100 text-indigo-600",
  facture: "bg-pink-100 text-pink-600",
  pec_request: "bg-teal-100 text-teal-600",
  invoice: "bg-pink-100 text-pink-600",
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
  send: "a envoye",
  merge: "a fusionne",
};

const ENTITY_LABELS: Record<string, string> = {
  case: "un dossier",
  cases: "les dossiers",
  document: "un document",
  payment: "un paiement",
  customer: "un client",
  client: "un client",
  customers: "les clients",
  user: "un utilisateur",
  invoice: "une facture",
  facture: "une facture",
  devis: "un devis",
  pec_request: "une PEC",
  settings: "les parametres",
  sync_customers: "les clients",
  sync_invoices: "les factures",
};

function getEntityLink(entityType: string, entityId: number): string | null {
  const routes: Record<string, string> = {
    case: `/cases/${entityId}`,
    customer: `/clients/${entityId}`,
    client: `/clients/${entityId}`,
    devis: `/devis/${entityId}`,
    facture: `/factures/${entityId}`,
    payment: "/paiements",
    pec_request: `/pec/${entityId}`,
    invoice: "/cosium-factures",
    document: `/cases`,
    sync_customers: "/admin",
    sync_invoices: "/admin",
  };
  return routes[entityType] || null;
}

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
  const router = useRouter();
  const { data, error, isLoading } = useSWR<AuditLogEntry[]>(
    "/audit-logs/recent?limit=8",
    { refreshInterval: 30000 },
  );

  if (isLoading) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
            <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
              Derniere activite
            </h3>
          </div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="flex items-center gap-3 animate-pulse">
              <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-700" />
              <div className="flex-1 space-y-1">
                <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
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
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
            Derniere activite
          </h3>
        </div>
        <Link
          href="/admin/audit"
          className="flex items-center gap-1 text-xs font-medium text-primary hover:underline"
        >
          Voir tout
          <ChevronRight className="h-3 w-3" aria-hidden="true" />
        </Link>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-text-secondary">Aucune activite recente.</p>
      ) : (
        <div className="space-y-1">
          {entries.map((entry) => {
            const Icon = ENTITY_ICONS[entry.entity_type] ?? Activity;
            const colorClass = ENTITY_COLORS[entry.entity_type] ?? "bg-gray-100 text-gray-600";
            const actionLabel = ACTION_LABELS[entry.action] ?? entry.action;
            const entityLabel = ENTITY_LABELS[entry.entity_type] ?? entry.entity_type;
            const userName = formatUserName(entry.user_email);
            const link = entry.entity_id ? getEntityLink(entry.entity_type, entry.entity_id) : null;

            const content = (
              <div className={`flex items-start gap-3 rounded-lg px-2 py-2 transition-colors ${link ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" : ""}`}>
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${colorClass}`}>
                  <Icon className="h-4 w-4" aria-hidden="true" />
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
                {link && (
                  <ChevronRight className="h-4 w-4 text-text-secondary shrink-0 mt-1" aria-hidden="true" />
                )}
              </div>
            );

            if (link) {
              return (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => router.push(link)}
                  className="w-full text-left"
                  aria-label={`${userName} ${actionLabel} ${entityLabel} ${entry.entity_id ? `#${entry.entity_id}` : ""}`}
                >
                  {content}
                </button>
              );
            }

            return <div key={entry.id}>{content}</div>;
          })}
        </div>
      )}
    </div>
  );
}
