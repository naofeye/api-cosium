"use client";

import { useState } from "react";
import { Check, Pencil, CheckCircle2, Undo2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { ConsolidatedField, FieldStatus } from "@/lib/types/pec-preparation";
import { STATUS_STYLES, getSourceColor, getSourceLabel } from "./consolidated-field-helpers";
import { StatusIcon, FieldStatusBadge, AlternativesTooltip } from "./ConsolidatedFieldParts";

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
