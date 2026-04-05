"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { RefreshCw, Users, FileText, Package } from "lucide-react";

interface SyncResult {
  created?: number;
  updated?: number;
  skipped?: number;
  fetched?: number;
  total?: number;
  note?: string;
}

const SYNC_ITEMS = [
  { key: "customers", label: "Clients", icon: Users, desc: "Synchroniser les fiches clients" },
  { key: "invoices", label: "Factures", icon: FileText, desc: "Importer les factures" },
  { key: "products", label: "Produits", icon: Package, desc: "Importer le catalogue produits" },
] as const;

export function ManualSync() {
  const [syncing, setSyncing] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, SyncResult>>({});

  const runSync = async (type: string) => {
    setSyncing(type);
    try {
      const result = await fetchJson<SyncResult>(`/sync/${type}`, { method: "POST" });
      setResults((prev) => ({ ...prev, [type]: result }));
    } catch {
      /* ignore */
    } finally {
      setSyncing(null);
    }
  };

  return (
    <>
      <h3 className="text-lg font-semibold text-text-primary mb-4">Synchronisation manuelle</h3>
      <p className="text-sm text-text-secondary mb-4">Lecture seule : Cosium vers OptiFlow.</p>
      <div className="space-y-4">
        {SYNC_ITEMS.map(({ key, label, icon: Icon, desc }) => (
          <div key={key} className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4">
            <div className="rounded-lg bg-blue-50 p-2.5">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold">{label}</h4>
              <p className="text-xs text-text-secondary">{desc}</p>
              {results[key] && (
                <p className="text-xs text-emerald-700 mt-1">
                  {results[key].created !== undefined &&
                    `${results[key].created} cree(s), ${results[key].updated} mis a jour`}
                  {results[key].fetched !== undefined && `${results[key].fetched} element(s) recupere(s)`}
                </p>
              )}
            </div>
            <Button variant="outline" onClick={() => runSync(key)} disabled={syncing !== null}>
              <RefreshCw className={`h-4 w-4 mr-1.5 ${syncing === key ? "animate-spin" : ""}`} />
              {syncing === key ? "Sync..." : "Synchroniser"}
            </Button>
          </div>
        ))}
      </div>
    </>
  );
}
