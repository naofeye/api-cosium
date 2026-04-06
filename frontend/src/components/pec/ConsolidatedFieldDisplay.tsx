"use client";

import { useState } from "react";
import { Check, Pencil, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { ConsolidatedField } from "@/lib/types/pec-preparation";

interface ConsolidatedFieldDisplayProps {
  label: string;
  field: ConsolidatedField | null;
  fieldName: string;
  validated?: boolean;
  onValidate?: (fieldName: string) => void;
  onCorrect?: (fieldName: string, newValue: string) => void;
}

const SOURCE_COLORS: Record<string, string> = {
  cosium: "bg-blue-100 text-blue-700",
  cosium_client: "bg-blue-100 text-blue-700",
  devis: "bg-emerald-100 text-emerald-700",
  document_ocr: "bg-orange-100 text-orange-700",
  ocr: "bg-orange-100 text-orange-700",
  manual: "bg-gray-100 text-gray-600",
};

function getSourceColor(source: string): string {
  const key = Object.keys(SOURCE_COLORS).find((k) => source.toLowerCase().includes(k));
  return key ? SOURCE_COLORS[key] : "bg-gray-100 text-gray-600";
}

function getSourceLabel(source: string, sourceLabel: string): string {
  return sourceLabel || source;
}

function ConfidenceIcon({ confidence }: { confidence: number }) {
  if (confidence >= 0.9) {
    return <CheckCircle2 className="h-4 w-4 text-emerald-500" aria-label="Confiance elevee" />;
  }
  if (confidence >= 0.6) {
    return <AlertTriangle className="h-4 w-4 text-amber-500" aria-label="Confiance moyenne" />;
  }
  return <XCircle className="h-4 w-4 text-red-500" aria-label="Confiance faible" />;
}

export function ConsolidatedFieldDisplay({
  label,
  field,
  fieldName,
  validated = false,
  onValidate,
  onCorrect,
}: ConsolidatedFieldDisplayProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");

  if (!field) {
    return (
      <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
        <span className="text-sm text-gray-500">{label}</span>
        <span className="text-sm text-red-500 italic">Manquant</span>
      </div>
    );
  }

  const displayValue = field.value !== null && field.value !== "" ? String(field.value) : "—";

  const handleStartEdit = () => {
    setEditValue(field.value !== null ? String(field.value) : "");
    setEditing(true);
  };

  const handleConfirmEdit = () => {
    if (onCorrect) {
      onCorrect(fieldName, editValue);
    }
    setEditing(false);
  };

  const handleCancelEdit = () => {
    setEditing(false);
  };

  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0 gap-3">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <span className="text-sm font-medium text-gray-700 w-36 shrink-0">{label}</span>
        {editing ? (
          <div className="flex items-center gap-2 flex-1">
            <input
              type="text"
              value={editValue}
              onChange={(e) => setEditValue(e.target.value)}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleConfirmEdit();
                if (e.key === "Escape") handleCancelEdit();
              }}
            />
            <Button size="sm" variant="primary" onClick={handleConfirmEdit} aria-label="Confirmer la correction">
              <Check className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="ghost" onClick={handleCancelEdit} aria-label="Annuler">
              Annuler
            </Button>
          </div>
        ) : (
          <>
            <span className={cn("text-sm", validated ? "text-emerald-700 font-medium" : "text-gray-900")}>
              {displayValue}
            </span>
            <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", getSourceColor(field.source))}>
              {getSourceLabel(field.source, field.source_label)}
            </span>
            <ConfidenceIcon confidence={field.confidence} />
          </>
        )}
      </div>
      {!editing && (
        <div className="flex items-center gap-1 shrink-0">
          {!validated && onValidate && (
            <Button size="sm" variant="ghost" onClick={() => onValidate(fieldName)} aria-label={`Valider ${label}`}>
              <Check className="h-3 w-3 mr-1" /> Valider
            </Button>
          )}
          {validated && (
            <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Valide
            </span>
          )}
          {onCorrect && (
            <Button size="sm" variant="ghost" onClick={handleStartEdit} aria-label={`Corriger ${label}`}>
              <Pencil className="h-3 w-3 mr-1" /> Corriger
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
