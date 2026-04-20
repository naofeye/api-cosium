"use client";

import { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  HelpCircle,
  Pencil,
} from "lucide-react";
import type { ConsolidatedField, FieldStatus } from "@/lib/types/pec-preparation";

export function StatusIcon({ status }: { status: FieldStatus }) {
  switch (status) {
    case "confirmed":
      return <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-label="Confirme" />;
    case "extracted":
      return <CheckCircle2 className="h-4 w-4 text-blue-500" aria-label="Extrait" />;
    case "deduced":
      return <HelpCircle className="h-4 w-4 text-amber-500" aria-label="Deduit" />;
    case "missing":
      return <XCircle className="h-4 w-4 text-red-500" aria-label="Manquant" />;
    case "conflict":
      return <AlertTriangle className="h-4 w-4 text-red-500" aria-label="Conflit entre sources" />;
    case "manual":
      return <Pencil className="h-4 w-4 text-gray-500" aria-label="Modifie manuellement" />;
    default:
      return <Info className="h-4 w-4 text-gray-400" aria-label="Inconnu" />;
  }
}

export function FieldStatusBadge({ status }: { status: FieldStatus }) {
  switch (status) {
    case "confirmed":
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700">
          confirme
        </span>
      );
    case "deduced":
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700">
          deduit
        </span>
      );
    case "manual":
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600">
          modifie manuellement
        </span>
      );
    case "conflict":
      return (
        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700">
          conflit
        </span>
      );
    default:
      return null;
  }
}

export function AlternativesTooltip({ field }: { field: ConsolidatedField }) {
  const [showAlternatives, setShowAlternatives] = useState(false);

  if (!field.alternatives || field.alternatives.length === 0) {
    return null;
  }

  return (
    <div className="relative inline-block">
      <button
        type="button"
        className="text-xs text-red-600 underline cursor-pointer hover:text-red-800"
        onClick={() => setShowAlternatives(!showAlternatives)}
        aria-label="Voir les alternatives"
      >
        {field.alternatives.length} alternative{field.alternatives.length > 1 ? "s" : ""}
      </button>
      {showAlternatives && (
        <div className="absolute z-10 mt-1 w-64 rounded-lg border border-gray-200 bg-white shadow-lg p-3 text-sm">
          <p className="text-xs font-medium text-gray-500 mb-2">Autres sources :</p>
          {field.alternatives.map((alt, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between py-1 border-b border-gray-100 last:border-0"
            >
              <span className="text-gray-900 font-medium">{String(alt.value ?? "\u2014")}</span>
              <span className="text-xs text-gray-500">
                {alt.source} ({Math.round(alt.confidence * 100)}%)
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
