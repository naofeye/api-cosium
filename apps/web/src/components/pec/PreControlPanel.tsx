"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  Shield,
  FileText,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { STATUS_CONFIG, DOCUMENT_LABELS } from "./pre-control-types";
import { PreControlIssues } from "./PreControlIssues";
import type { PreControlResult } from "./pre-control-types";

interface PreControlPanelProps {
  preparationId: string;
  onOpenAudit: () => void;
}

export function PreControlPanel({ preparationId, onOpenAudit }: PreControlPanelProps) {
  const [data, setData] = useState<PreControlResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchJson<PreControlResult>(`/pec-preparations/${preparationId}/precontrol`)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Erreur de chargement");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [preparationId]);

  if (loading) {
    return (
      <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5 mb-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-48 mb-4" />
        <div className="h-4 bg-gray-100 rounded w-64 mb-2" />
        <div className="h-4 bg-gray-100 rounded w-40" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-5 mb-6">
        <p className="text-sm text-red-700">{error ?? "Impossible de charger le pré-contrôle"}</p>
      </div>
    );
  }

  const config = STATUS_CONFIG[data.status] ?? STATUS_CONFIG.incomplet;
  const StatusIcon = config.icon;

  const allDocuments = [
    ...["ordonnance", "devis"].map((role) => ({
      role,
      label: DOCUMENT_LABELS[role] ?? role,
      present: data.pieces_presentes.includes(role),
      required: true,
    })),
    ...["attestation_mutuelle", "carte_vitale"].map((role) => ({
      role,
      label: DOCUMENT_LABELS[role] ?? role,
      present: data.pieces_presentes.includes(role),
      required: false,
    })),
  ];

  return (
    <div className={cn("rounded-xl border shadow-sm mb-6", config.border, config.bg)}>
      {/* Section 1: Statut global */}
      <div className="p-5 border-b border-gray-200/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={cn("p-2 rounded-lg", config.bg)}>
              <Shield className={cn("h-6 w-6", config.color)} aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-gray-900">Pré-contrôle PEC</h3>
                <span
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium",
                    config.bg,
                    config.color,
                  )}
                >
                  <StatusIcon className="h-3.5 w-3.5" aria-hidden="true" />
                  {data.status_label}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                Complétude : {Math.round(data.completude_score)}% &mdash;{" "}
                {data.champs_confirmes} confirmé(s), {data.champs_extraits} extrait(s),{" "}
                {data.champs_manquants > 0 && (
                  <span className="text-red-600 font-medium">{data.champs_manquants} manquant(s)</span>
                )}
                {data.champs_manquants === 0 && "aucun manquant"}
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onOpenAudit} aria-label="Voir le journal d'audit">
            <History className="h-4 w-4 mr-1" /> Journal d&apos;audit
          </Button>
        </div>

        {/* Complétude gauge */}
        <div className="mt-3">
          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all",
                data.completude_score >= 80 ? "bg-emerald-500" :
                data.completude_score >= 50 ? "bg-amber-500" : "bg-red-500",
              )}
              style={{ width: `${Math.min(data.completude_score, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Section 2: Pièces justificatives */}
      <div className="p-5 border-b border-gray-200/50">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          <FileText className="h-3.5 w-3.5 inline mr-1" aria-hidden="true" />
          Pièces justificatives
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {allDocuments.map((doc) => (
            <div key={doc.role} className="flex items-center gap-2 text-sm">
              {doc.present ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" aria-label="Présent" />
              ) : (
                <XCircle
                  className={cn(
                    "h-4 w-4 shrink-0",
                    doc.required ? "text-red-500" : "text-amber-400",
                  )}
                  aria-label={doc.required ? "Manquant (requis)" : "Manquant (recommandé)"}
                />
              )}
              <span className={cn(doc.present ? "text-gray-700" : doc.required ? "text-red-600 font-medium" : "text-amber-600")}>
                {doc.label}
                {!doc.present && doc.required && " (requis)"}
                {!doc.present && !doc.required && " (recommandé)"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Points à vérifier */}
      <PreControlIssues
        erreurs_bloquantes={data.erreurs_bloquantes}
        alertes_verification={data.alertes_verification}
        points_vigilance={data.points_vigilance}
      />
    </div>
  );
}
