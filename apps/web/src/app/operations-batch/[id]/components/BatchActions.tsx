"use client";

import Link from "next/link";
import { CheckCircle, ClipboardCheck, FileDown } from "lucide-react";

interface BatchActionsProps {
  clientsPrets: number;
  totalClients: number;
  pecPreparedCount: number | null;
  preparingPec: boolean;
  onPreparePec: () => void;
  onExport: () => void;
}

export function BatchActions({
  clientsPrets,
  totalClients,
  pecPreparedCount,
  preparingPec,
  onPreparePec,
  onExport,
}: BatchActionsProps) {
  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        {clientsPrets > 0 && pecPreparedCount === null && (
          <button
            onClick={onPreparePec}
            disabled={preparingPec}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <ClipboardCheck className="h-4 w-4" aria-hidden="true" />
            {preparingPec ? "Preparation en cours..." : "Preparer toutes les PEC"}
          </button>
        )}

        <button
          onClick={onExport}
          className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
        >
          <FileDown className="h-4 w-4" aria-hidden="true" />
          Exporter Excel
        </button>
      </div>

      {pecPreparedCount !== null && (
        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-center gap-3">
            <CheckCircle className="h-6 w-6 text-emerald-600" aria-hidden="true" />
            <div>
              <p className="font-semibold text-emerald-900">
                {pecPreparedCount} fiches PEC preparees sur {totalClients} dossiers
              </p>
              <Link
                href="/pec-dashboard"
                className="mt-1 inline-block text-sm text-emerald-700 hover:underline"
              >
                Voir le tableau de bord PEC
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
