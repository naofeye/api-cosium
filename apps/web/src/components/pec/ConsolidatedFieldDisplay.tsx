"use client";

import { useState } from "react";
import { Check, Pencil, CheckCircle2, AlertTriangle, XCircle, Info, HelpCircle, Undo2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { ConsolidatedField, FieldStatus } from "@/lib/types/pec-preparation";

interface ConsolidatedFieldDisplayProps {
  label: string;
  field: ConsolidatedField | null;
  fieldName: string;
  validated?: boolean;
  /** Original value before manual correction (from user_corrections) */
  originalValue?: string | null;
  /** Reason for the correction (from user_corrections) */
  correctionReason?: string | null;
  onValidate?: (fieldName: string) => void;
  onCorrect?: (fieldName: string, newValue: string, reason?: string) => void;
  /** Callback to undo a correction (restore original value) */
  onUndoCorrection?: (fieldName: string, originalValue: string) => void;
}

const SOURCE_COLORS: Record<string, string> = {
  cosium: "bg-blue-100 text-blue-700",
  cosium_client: "bg-blue-100 text-blue-700",
  devis: "bg-emerald-100 text-emerald-700",
  document_ocr: "bg-orange-100 text-orange-700",
  ocr: "bg-orange-100 text-orange-700",
  manual: "bg-gray-100 text-gray-600",
};

/**
 * Border/background styling per FieldStatus.
 */
const STATUS_STYLES: Record<FieldStatus, string> = {
  confirmed: "border-2 border-emerald-400 bg-emerald-50/30",
  extracted: "border border-blue-200 bg-white",
  deduced: "border-2 border-amber-300 bg-amber-50/20",
  missing: "border-2 border-dashed border-red-300 bg-red-50/30",
  conflict: "border-2 border-red-400 bg-red-50/20",
  manual: "border-2 border-gray-300 bg-gray-50/30",
};

function getSourceColor(source: string): string {
  const key = Object.keys(SOURCE_COLORS).find((k) => source.toLowerCase().includes(k));
  return key ? SOURCE_COLORS[key] : "bg-gray-100 text-gray-600";
}

function getSourceLabel(source: string, sourceLabel: string): string {
  return sourceLabel || source;
}

function StatusIcon({ status }: { status: FieldStatus }) {
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

function FieldStatusBadge({ status }: { status: FieldStatus }) {
  switch (status) {
    case "confirmed":
      return <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700">confirme</span>;
    case "deduced":
      return <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-amber-100 text-amber-700">deduit</span>;
    case "manual":
      return <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600">modifie manuellement</span>;
    case "conflict":
      return <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-red-100 text-red-700">conflit</span>;
    default:
      return null;
  }
}

function AlternativesTooltip({ field }: { field: ConsolidatedField }) {
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
            <div key={idx} className="flex items-center justify-between py-1 border-b border-gray-100 last:border-0">
              <span className="text-gray-900 font-medium">{String(alt.value ?? "\u2014")}</span>
              <span className="text-xs text-gray-500">{alt.source} ({Math.round(alt.confidence * 100)}%)</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ConsolidatedFieldDisplay({
  label,
  field,
  fieldName,
  validated = false,
  originalValue,
  correctionReason,
  onValidate,
  onCorrect,
  onUndoCorrection,
}: ConsolidatedFieldDisplayProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [editReason, setEditReason] = useState("");

  const handleConfirmEdit = () => {
    if (onCorrect) {
      onCorrect(fieldName, editValue, editReason || undefined);
    }
    setEditing(false);
    setEditReason("");
  };

  const handleCancelEdit = () => {
    setEditing(false);
    setEditReason("");
  };

  const handleUndoCorrection = () => {
    if (onUndoCorrection && originalValue !== null && originalValue !== undefined) {
      onUndoCorrection(fieldName, originalValue);
    }
  };

  const isManuallyCorreected = field?.status === "manual" && originalValue !== null && originalValue !== undefined;

  // Missing field (null) — show empty state with red dashed border
  if (!field) {
    return (
      <div
        className={cn(
          "flex items-center justify-between py-2 px-3 rounded-lg cursor-pointer hover:bg-red-50/60 transition-colors",
          STATUS_STYLES.missing,
        )}
        onClick={() => {
          if (onCorrect) {
            setEditValue("");
            setEditing(true);
          }
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && onCorrect) {
            setEditValue("");
            setEditing(true);
          }
        }}
      >
        <span className="text-sm text-gray-500">{label}</span>
        {editing ? (
          <div className="flex flex-col gap-2 flex-1 ml-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                className="flex-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
                autoFocus
                placeholder="Saisir la valeur manquante..."
                onKeyDown={(e) => {
                  e.stopPropagation();
                  if (e.key === "Enter") handleConfirmEdit();
                  if (e.key === "Escape") handleCancelEdit();
                }}
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={editReason}
                onChange={(e) => setEditReason(e.target.value)}
                className="flex-1 rounded-lg border border-gray-200 px-3 py-1 text-xs text-gray-600 focus:ring-1 focus:ring-blue-400 focus:border-blue-400 outline-none"
                placeholder="Raison (optionnel)..."
                onKeyDown={(e) => {
                  e.stopPropagation();
                  if (e.key === "Enter") handleConfirmEdit();
                  if (e.key === "Escape") handleCancelEdit();
                }}
              />
              <Button size="sm" variant="primary" onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleConfirmEdit(); }} aria-label="Confirmer">
                <Check className="h-3 w-3" />
              </Button>
              <Button size="sm" variant="ghost" onClick={(e: React.MouseEvent) => { e.stopPropagation(); handleCancelEdit(); }} aria-label="Annuler">
                Annuler
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <StatusIcon status="missing" />
            <span className="text-sm text-red-500 italic">Donnee manquante — cliquer pour completer</span>
          </div>
        )}
      </div>
    );
  }

  const displayValue = field.value !== null && field.value !== "" ? String(field.value) : "\u2014";
  const fieldStatus: FieldStatus = field.status || "extracted";

  const handleStartEdit = () => {
    setEditValue(field.value !== null ? String(field.value) : "");
    setEditReason("");
    setEditing(true);
  };

  // Use status-based border styling
  const borderStyle = validated ? STATUS_STYLES.confirmed : STATUS_STYLES[fieldStatus];

  return (
    <div className={cn("py-2 px-3 rounded-lg gap-3", borderStyle)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <span className="text-sm font-medium text-gray-700 w-36 shrink-0">{label}</span>
          {editing ? (
            <div className="flex flex-col gap-2 flex-1">
              <div className="flex items-center gap-2">
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
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editReason}
                  onChange={(e) => setEditReason(e.target.value)}
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-1 text-xs text-gray-600 focus:ring-1 focus:ring-blue-400 focus:border-blue-400 outline-none"
                  placeholder="Raison (optionnel)..."
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
            </div>
          ) : (
            <>
              {/* Show original crossed out + new value for manual corrections */}
              {isManuallyCorreected && (
                <span className="text-sm text-gray-400 line-through mr-1">
                  {originalValue}
                </span>
              )}
              <span className={cn("text-sm", validated ? "text-emerald-700 font-medium" : "text-gray-900")}>
                {displayValue}
              </span>
              <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", getSourceColor(field.source))}>
                {getSourceLabel(field.source, field.source_label)}
              </span>
              <StatusIcon status={fieldStatus} />
              <FieldStatusBadge status={fieldStatus} />
              {fieldStatus === "conflict" && <AlternativesTooltip field={field} />}
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
            {isManuallyCorreected && onUndoCorrection && (
              <Button size="sm" variant="ghost" onClick={handleUndoCorrection} aria-label={`Annuler la correction de ${label}`}>
                <Undo2 className="h-3 w-3 mr-1" /> Restaurer
              </Button>
            )}
            {onCorrect && (
              <Button size="sm" variant="ghost" onClick={handleStartEdit} aria-label={`Corriger ${label}`}>
                <Pencil className="h-3 w-3 mr-1" /> Corriger
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Show correction reason if present */}
      {isManuallyCorreected && correctionReason && !editing && (
        <p className="text-xs text-gray-400 mt-1 ml-[calc(9rem+0.75rem)]">
          Raison : {correctionReason}
        </p>
      )}
    </div>
  );
}
