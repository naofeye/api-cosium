"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Info,
  Shield,
  FileText,
  ChevronDown,
  ChevronUp,
  History,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";

interface PreControlResult {
  status: "pret" | "incomplet" | "conflits" | "validation_requise";
  status_label: string;
  completude_score: number;
  pieces_presentes: string[];
  pieces_manquantes: string[];
  pieces_recommandees_manquantes: string[];
  erreurs_bloquantes: string[];
  alertes_verification: string[];
  points_vigilance: string[];
  champs_confirmes: number;
  champs_deduits: number;
  champs_en_conflit: number;
  champs_manquants: number;
  champs_manuels: number;
  champs_extraits: number;
}

const STATUS_CONFIG: Record<
  string,
  { color: string; bg: string; border: string; icon: typeof CheckCircle2; label: string }
> = {
  pret: {
    color: "text-emerald-700",
    bg: "bg-emerald-50",
    border: "border-emerald-200",
    icon: CheckCircle2,
    label: "Pret",
  },
  incomplet: {
    color: "text-red-700",
    bg: "bg-red-50",
    border: "border-red-200",
    icon: XCircle,
    label: "Incomplet",
  },
  conflits: {
    color: "text-amber-700",
    bg: "bg-amber-50",
    border: "border-amber-200",
    icon: AlertTriangle,
    label: "Conflits",
  },
  validation_requise: {
    color: "text-blue-700",
    bg: "bg-blue-50",
    border: "border-blue-200",
    icon: Info,
    label: "Validation requise",
  },
};

const DOCUMENT_LABELS: Record<string, string> = {
  ordonnance: "Ordonnance",
  devis: "Devis signe",
  attestation_mutuelle: "Attestation mutuelle",
  carte_vitale: "Carte vitale",
  facture: "Facture",
  autre: "Autre document",
};

interface PreControlPanelProps {
  preparationId: string;
  onOpenAudit: () => void;
}

export function PreControlPanel({ preparationId, onOpenAudit }: PreControlPanelProps) {
  const [data, setData] = useState<PreControlResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorsExpanded, setErrorsExpanded] = useState(false);
  const [warningsExpanded, setWarningsExpanded] = useState(false);
  const [infoExpanded, setInfoExpanded] = useState(false);

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
        <p className="text-sm text-red-700">{error ?? "Impossible de charger le pre-controle"}</p>
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

  const totalIssues =
    data.erreurs_bloquantes.length +
    data.alertes_verification.length +
    data.points_vigilance.length;

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
                <h3 className="text-sm font-semibold text-gray-900">Pre-controle PEC</h3>
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
                Completude : {Math.round(data.completude_score)}% &mdash;{" "}
                {data.champs_confirmes} confirme(s), {data.champs_extraits} extrait(s),{" "}
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

        {/* Completude gauge */}
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

      {/* Section 2: Pieces justificatives */}
      <div className="p-5 border-b border-gray-200/50">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
          <FileText className="h-3.5 w-3.5 inline mr-1" aria-hidden="true" />
          Pieces justificatives
        </h4>
        <div className="grid grid-cols-2 gap-2">
          {allDocuments.map((doc) => (
            <div key={doc.role} className="flex items-center gap-2 text-sm">
              {doc.present ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" aria-label="Present" />
              ) : (
                <XCircle
                  className={cn(
                    "h-4 w-4 shrink-0",
                    doc.required ? "text-red-500" : "text-amber-400",
                  )}
                  aria-label={doc.required ? "Manquant (requis)" : "Manquant (recommande)"}
                />
              )}
              <span className={cn(doc.present ? "text-gray-700" : doc.required ? "text-red-600 font-medium" : "text-amber-600")}>
                {doc.label}
                {!doc.present && doc.required && " (requis)"}
                {!doc.present && !doc.required && " (recommande)"}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Section 3: Points a verifier */}
      {totalIssues > 0 && (
        <div className="p-5">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
            Points a verifier
          </h4>
          <div className="space-y-2">
            {/* Erreurs bloquantes */}
            {data.erreurs_bloquantes.length > 0 && (
              <div>
                <button
                  type="button"
                  className="flex items-center gap-2 w-full text-left text-sm font-medium text-red-700 hover:text-red-800"
                  onClick={() => setErrorsExpanded(!errorsExpanded)}
                  aria-expanded={errorsExpanded}
                >
                  <XCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {data.erreurs_bloquantes.length} erreur(s) bloquante(s)
                  {errorsExpanded ? (
                    <ChevronUp className="h-3 w-3 ml-auto" />
                  ) : (
                    <ChevronDown className="h-3 w-3 ml-auto" />
                  )}
                </button>
                {errorsExpanded && (
                  <ul className="mt-1 ml-6 space-y-1">
                    {data.erreurs_bloquantes.map((msg, i) => (
                      <li key={i} className="text-xs text-red-600">&bull; {msg}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Alertes */}
            {data.alertes_verification.length > 0 && (
              <div>
                <button
                  type="button"
                  className="flex items-center gap-2 w-full text-left text-sm font-medium text-amber-700 hover:text-amber-800"
                  onClick={() => setWarningsExpanded(!warningsExpanded)}
                  aria-expanded={warningsExpanded}
                >
                  <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {data.alertes_verification.length} alerte(s) a verifier
                  {warningsExpanded ? (
                    <ChevronUp className="h-3 w-3 ml-auto" />
                  ) : (
                    <ChevronDown className="h-3 w-3 ml-auto" />
                  )}
                </button>
                {warningsExpanded && (
                  <ul className="mt-1 ml-6 space-y-1">
                    {data.alertes_verification.map((msg, i) => (
                      <li key={i} className="text-xs text-amber-600">&bull; {msg}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Points de vigilance */}
            {data.points_vigilance.length > 0 && (
              <div>
                <button
                  type="button"
                  className="flex items-center gap-2 w-full text-left text-sm font-medium text-blue-700 hover:text-blue-800"
                  onClick={() => setInfoExpanded(!infoExpanded)}
                  aria-expanded={infoExpanded}
                >
                  <Info className="h-4 w-4 shrink-0" aria-hidden="true" />
                  {data.points_vigilance.length} point(s) de vigilance
                  {infoExpanded ? (
                    <ChevronUp className="h-3 w-3 ml-auto" />
                  ) : (
                    <ChevronDown className="h-3 w-3 ml-auto" />
                  )}
                </button>
                {infoExpanded && (
                  <ul className="mt-1 ml-6 space-y-1">
                    {data.points_vigilance.map((msg, i) => (
                      <li key={i} className="text-xs text-blue-600">&bull; {msg}</li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {totalIssues === 0 && (
        <div className="p-5">
          <div className="flex items-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            Aucun point bloquant detecte. Le dossier est pret pour soumission.
          </div>
        </div>
      )}
    </div>
  );
}
