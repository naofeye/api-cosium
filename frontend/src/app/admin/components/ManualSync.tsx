"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import {
  RefreshCw,
  Users,
  FileText,
  Package,
  CreditCard,
  Stethoscope,
  Calendar,
  Shield,
  PlayCircle,
  FolderDown,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

interface SyncResult {
  created?: number;
  updated?: number;
  skipped?: number;
  unchanged?: number;
  total?: number;
  note?: string;
  // Pour sync/all qui retourne un objet par type
  customers?: SyncResult;
  invoices?: SyncResult;
  payments?: SyncResult;
  prescriptions?: SyncResult;
  [key: string]: unknown;
}

const SYNC_ITEMS = [
  { key: "customers", label: "Clients", icon: Users, desc: "Fiches clients Cosium (3 742)" },
  { key: "invoices", label: "Factures", icon: FileText, desc: "Factures, devis, avoirs (25 161)" },
  { key: "payments", label: "Paiements", icon: CreditCard, desc: "Paiements de factures (25 448)" },
  { key: "prescriptions", label: "Ordonnances", icon: Stethoscope, desc: "Ordonnances optiques (6 785)" },
  { key: "products", label: "Produits", icon: Package, desc: "Catalogue produits (echantillon)" },
] as const;

const DOCUMENT_ITEMS = [
  { key: "cosium-documents/sync-all", label: "Documents clients", icon: FolderDown, desc: "Telecharger tous les documents depuis Cosium (lent, ~1 doc/sec)" },
] as const;

const REFERENCE_ITEMS = [
  { key: "cosium/sync-reference", label: "Donnees reference", icon: Shield, desc: "Calendrier, mutuelles, medecins, marques, fournisseurs, tags, sites" },
] as const;

function formatResult(r: SyncResult): string {
  const parts: string[] = [];
  if (r.created !== undefined) parts.push(`${r.created} cree(s)`);
  if (r.updated !== undefined && r.updated > 0) parts.push(`${r.updated} mis a jour`);
  if (r.unchanged !== undefined && r.unchanged > 0) parts.push(`${r.unchanged} inchanges`);
  if (r.skipped !== undefined && r.skipped > 0) parts.push(`${r.skipped} ignores`);
  if (r.total !== undefined) parts.push(`${r.total} total`);
  return parts.join(", ") || "Termine";
}

const SYNC_ALL_STEPS = ["customers", "invoices", "payments", "prescriptions"] as const;

export function ManualSync() {
  const [syncing, setSyncing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SyncResult>>({});
  const [syncAllRunning, setSyncAllRunning] = useState(false);
  const [syncAllStep, setSyncAllStep] = useState(0);
  const [syncAllTotal] = useState(SYNC_ALL_STEPS.length);
  const [syncAllStatus, setSyncAllStatus] = useState<Record<string, "pending" | "success" | "error">>({});
  const [syncSummary, setSyncSummary] = useState<string | null>(null);

  const runSync = async (type: string) => {
    setSyncing(type);
    try {
      const endpoint = type.startsWith("cosium/") ? `/${type}` : `/sync/${type}`;
      const result = await fetchJson<SyncResult>(endpoint, { method: "POST" });
      setResults((prev) => ({ ...prev, [type]: result }));
    } catch {
      setResults((prev) => ({ ...prev, [type]: { note: "Erreur lors de la synchronisation" } }));
    } finally {
      setSyncing(null);
    }
  };

  const runSyncAll = async () => {
    setSyncAllRunning(true);
    setSyncing("all");
    setSyncAllStep(0);
    const statusMap: Record<string, "pending" | "success" | "error"> = {};
    for (const s of SYNC_ALL_STEPS) statusMap[s] = "pending";
    setSyncAllStatus({ ...statusMap });

    for (let i = 0; i < SYNC_ALL_STEPS.length; i++) {
      const step = SYNC_ALL_STEPS[i];
      setSyncAllStep(i + 1);
      setSyncing(step);
      try {
        const result = await fetchJson<SyncResult>(`/sync/${step}`, { method: "POST" });
        setResults((prev) => ({ ...prev, [step]: result }));
        statusMap[step] = "success";
      } catch {
        setResults((prev) => ({ ...prev, [step]: { note: "Erreur lors de la synchronisation" } }));
        statusMap[step] = "error";
      }
      setSyncAllStatus({ ...statusMap });
    }

    const errorCount = Object.values(statusMap).filter((s) => s === "error").length;
    setSyncAllRunning(false);
    setSyncing(null);
    if (errorCount > 0) {
      setSyncSummary(`Synchronisation incomplete : ${errorCount} etape(s) en erreur.`);
    } else {
      setSyncSummary(null);
    }
  };

  const isDisabled = syncing !== null;

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-text-primary">Synchronisation Cosium</h3>
          <p className="text-sm text-text-secondary">Lecture seule : Cosium → OptiFlow.</p>
        </div>
        <Button onClick={runSyncAll} disabled={isDisabled} className="gap-2">
          <PlayCircle className={`h-4 w-4 ${syncAllRunning ? "animate-spin" : ""}`} />
          {syncAllRunning ? "Sync en cours..." : "Tout synchroniser"}
        </Button>
      </div>

      {/* Sync All progress */}
      {syncAllRunning && (
        <div className="mb-4 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div className="flex items-center gap-2 mb-2">
            <Loader2 className="h-4 w-4 animate-spin text-blue-600" aria-hidden="true" />
            <p className="text-sm font-medium text-blue-800">
              Synchronisation en cours... {syncAllStep}/{syncAllTotal} etapes
            </p>
          </div>
          <div className="w-full bg-blue-100 rounded-full h-2 mb-3">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${(syncAllStep / syncAllTotal) * 100}%` }}
            />
          </div>
          <div className="space-y-1">
            {SYNC_ALL_STEPS.map((step) => {
              const status = syncAllStatus[step];
              const label = SYNC_ITEMS.find((s) => s.key === step)?.label ?? step;
              return (
                <div key={step} className="flex items-center gap-2 text-sm">
                  {status === "success" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                  ) : status === "error" ? (
                    <XCircle className="h-4 w-4 text-red-600" aria-hidden="true" />
                  ) : syncing === step ? (
                    <Loader2 className="h-4 w-4 animate-spin text-blue-600" aria-hidden="true" />
                  ) : (
                    <div className="h-4 w-4 rounded-full border border-gray-300" />
                  )}
                  <span className={status === "success" ? "text-emerald-700" : status === "error" ? "text-red-700" : "text-gray-600"}>
                    {label}
                    {status === "success" && results[step] && ` — ${formatResult(results[step])}`}
                    {status === "error" && " — Erreur"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Completed sync all summary */}
      {!syncAllRunning && Object.keys(syncAllStatus).length > 0 && (() => {
        const hasErrors = Object.values(syncAllStatus).some((s) => s === "error");
        return (
        <div className={`mb-4 rounded-lg border p-4 ${hasErrors ? "border-red-200 bg-red-50" : "border-emerald-200 bg-emerald-50"}`}>
          <p className={`text-sm font-medium mb-2 ${hasErrors ? "text-red-800" : "text-emerald-800"}`}>
            {hasErrors ? "Synchronisation incomplete — certaines etapes ont echoue" : "Synchronisation terminee avec succes"}
          </p>
          <div className="space-y-1">
            {SYNC_ALL_STEPS.map((step) => {
              const status = syncAllStatus[step];
              const label = SYNC_ITEMS.find((s) => s.key === step)?.label ?? step;
              return (
                <div key={step} className="flex items-center gap-2 text-sm">
                  {status === "success" ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                  ) : (
                    <XCircle className="h-4 w-4 text-red-600" aria-hidden="true" />
                  )}
                  <span className={status === "success" ? "text-emerald-700" : "text-red-700"}>
                    {label}
                    {status === "success" && results[step] && ` — ${formatResult(results[step])}`}
                    {status === "error" && " — Erreur"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
        );
      })()}

      <div className="space-y-3">
        <h4 className="text-sm font-medium text-text-secondary uppercase tracking-wide">Donnees principales</h4>
        {SYNC_ITEMS.map(({ key, label, icon: Icon, desc }) => (
          <SyncRow
            key={key}
            syncKey={key}
            label={label}
            icon={Icon}
            desc={desc}
            result={results[key]}
            syncing={syncing}
            disabled={isDisabled}
            onSync={runSync}
          />
        ))}

        <h4 className="text-sm font-medium text-text-secondary uppercase tracking-wide mt-6">Documents</h4>
        {DOCUMENT_ITEMS.map(({ key, label, icon: Icon, desc }) => (
          <SyncRow
            key={key}
            syncKey={key}
            label={label}
            icon={Icon}
            desc={desc}
            result={results[key]}
            syncing={syncing}
            disabled={isDisabled}
            onSync={runSync}
          />
        ))}

        <h4 className="text-sm font-medium text-text-secondary uppercase tracking-wide mt-6">Donnees de reference</h4>
        {REFERENCE_ITEMS.map(({ key, label, icon: Icon, desc }) => (
          <SyncRow
            key={key}
            syncKey={key}
            label={label}
            icon={Icon}
            desc={desc}
            result={results[key]}
            syncing={syncing}
            disabled={isDisabled}
            onSync={runSync}
          />
        ))}
      </div>
    </>
  );
}

function SyncRow({
  syncKey, label, icon: Icon, desc, result, syncing, disabled, onSync,
}: {
  syncKey: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  desc: string;
  result?: SyncResult;
  syncing: string | null;
  disabled: boolean;
  onSync: (key: string) => void;
}) {
  const isSyncing = syncing === syncKey;
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm flex items-center gap-4">
      <div className="rounded-lg bg-blue-50 p-2.5 dark:bg-blue-900/20">
        <Icon className="h-5 w-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-semibold">{label}</h4>
        <p className="text-xs text-text-secondary">{desc}</p>
        {result && (
          <p className={`text-xs mt-1 ${result.note?.includes("Erreur") ? "text-red-600" : "text-emerald-700"}`}>
            {result.note || formatResult(result)}
          </p>
        )}
      </div>
      <Button variant="outline" size="sm" onClick={() => onSync(syncKey)} disabled={disabled}>
        <RefreshCw className={`h-4 w-4 mr-1.5 ${isSyncing ? "animate-spin" : ""}`} aria-hidden="true" />
        {isSyncing ? "Sync..." : "Lancer"}
      </Button>
    </div>
  );
}
