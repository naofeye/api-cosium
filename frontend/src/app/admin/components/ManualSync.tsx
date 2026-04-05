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

export function ManualSync() {
  const [syncing, setSyncing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SyncResult>>({});
  const [syncAllRunning, setSyncAllRunning] = useState(false);

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
    try {
      const result = await fetchJson<SyncResult>("/sync/all", { method: "POST" });
      // Le endpoint /sync/all retourne un objet avec un resultat par type
      setResults((prev) => ({
        ...prev,
        all: result,
        ...(result.customers ? { customers: result.customers as SyncResult } : {}),
        ...(result.invoices ? { invoices: result.invoices as SyncResult } : {}),
        ...(result.payments ? { payments: result.payments as SyncResult } : {}),
        ...(result.prescriptions ? { prescriptions: result.prescriptions as SyncResult } : {}),
      }));
    } catch {
      setResults((prev) => ({ ...prev, all: { note: "Erreur lors de la synchronisation globale" } }));
    } finally {
      setSyncAllRunning(false);
      setSyncing(null);
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

      {results.all?.note && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
          {results.all.note}
        </div>
      )}

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
