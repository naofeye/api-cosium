"use client";

import { CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConsolidatedField } from "@/lib/types/pec-preparation";

interface CorrectionRow {
  label: string;
  od: ConsolidatedField | null;
  og: ConsolidatedField | null;
}

interface CorrectionTableProps {
  rows: CorrectionRow[];
  prescripteur?: ConsolidatedField | null;
  dateOrdonnance?: ConsolidatedField | null;
}

function ConfidenceBadge({ confidence }: { confidence: number }) {
  if (confidence >= 0.9) {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500 inline ml-1" aria-label="Confiance elevee" />;
  }
  if (confidence >= 0.6) {
    return <AlertTriangle className="h-4 w-4 text-amber-500 inline ml-1" aria-label="Confiance moyenne" />;
  }
  return <XCircle className="h-4 w-4 text-red-500 inline ml-1" aria-label="Confiance faible" />;
}

function CellValue({ field }: { field: ConsolidatedField | null }) {
  if (!field || field.value === null) {
    return <span className="text-gray-400 italic">—</span>;
  }
  const val = typeof field.value === "number" ? field.value.toFixed(2) : String(field.value);
  return (
    <span className={cn("tabular-nums", field.confidence < 0.6 ? "text-red-700 font-medium" : "text-gray-900")}>
      {val}
      <ConfidenceBadge confidence={field.confidence} />
    </span>
  );
}

export function CorrectionTable({ rows, prescripteur, dateOrdonnance }: CorrectionTableProps) {
  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th scope="col" className="px-4 py-2.5 text-left font-medium text-gray-600 w-28" />
              <th scope="col" className="px-4 py-2.5 text-center font-medium text-gray-600">OD (Oeil droit)</th>
              <th scope="col" className="px-4 py-2.5 text-center font-medium text-gray-600">OG (Oeil gauche)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label} className="border-b last:border-0">
                <td className="px-4 py-2.5 font-medium text-gray-700">{row.label}</td>
                <td className="px-4 py-2.5 text-center">
                  <CellValue field={row.od} />
                </td>
                <td className="px-4 py-2.5 text-center">
                  <CellValue field={row.og} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {(prescripteur || dateOrdonnance) && (
        <div className="flex gap-6 text-sm text-gray-600 px-1">
          {prescripteur && prescripteur.value && (
            <span>
              <span className="font-medium">Prescripteur :</span> {String(prescripteur.value)}
            </span>
          )}
          {dateOrdonnance && dateOrdonnance.value && (
            <span>
              <span className="font-medium">Date ordonnance :</span> {String(dateOrdonnance.value)}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
