"use client";

import { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, Info, ChevronDown, ChevronUp } from "lucide-react";

interface PreControlIssuesProps {
  erreurs_bloquantes: string[];
  alertes_verification: string[];
  points_vigilance: string[];
}

function CollapsibleList({
  count,
  label,
  colorClass,
  icon: Icon,
  items,
}: {
  count: number;
  label: string;
  colorClass: string;
  icon: typeof XCircle;
  items: string[];
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div>
      <button
        type="button"
        className={`flex items-center gap-2 w-full text-left text-sm font-medium ${colorClass}`}
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
        {count} {label}
        {expanded ? (
          <ChevronUp className="h-3 w-3 ml-auto" />
        ) : (
          <ChevronDown className="h-3 w-3 ml-auto" />
        )}
      </button>
      {expanded && (
        <ul className="mt-1 ml-6 space-y-1">
          {items.map((msg, i) => (
            <li key={i} className={`text-xs ${colorClass.replace("font-medium", "").replace("hover:", "")}`}>
              &bull; {msg}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function PreControlIssues({
  erreurs_bloquantes,
  alertes_verification,
  points_vigilance,
}: PreControlIssuesProps) {
  const totalIssues = erreurs_bloquantes.length + alertes_verification.length + points_vigilance.length;

  if (totalIssues === 0) {
    return (
      <div className="p-5">
        <div className="flex items-center gap-2 text-sm text-emerald-700">
          <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
          Aucun point bloquant détecté. Le dossier est prêt pour soumission.
        </div>
      </div>
    );
  }

  return (
    <div className="p-5">
      <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
        Points à vérifier
      </h4>
      <div className="space-y-2">
        {erreurs_bloquantes.length > 0 && (
          <CollapsibleList
            count={erreurs_bloquantes.length}
            label="erreur(s) bloquante(s)"
            colorClass="text-red-700 hover:text-red-800"
            icon={XCircle}
            items={erreurs_bloquantes}
          />
        )}
        {alertes_verification.length > 0 && (
          <CollapsibleList
            count={alertes_verification.length}
            label="alerte(s) à vérifier"
            colorClass="text-amber-700 hover:text-amber-800"
            icon={AlertTriangle}
            items={alertes_verification}
          />
        )}
        {points_vigilance.length > 0 && (
          <CollapsibleList
            count={points_vigilance.length}
            label="point(s) de vigilance"
            colorClass="text-blue-700 hover:text-blue-800"
            icon={Info}
            items={points_vigilance}
          />
        )}
      </div>
    </div>
  );
}
