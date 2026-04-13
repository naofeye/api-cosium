import { AlertTriangle } from "lucide-react";
import { CompletionGauge } from "@/components/pec/CompletionGauge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { ConsolidatedClientProfile, PecPreparation } from "@/lib/types/pec-preparation";
import { STATUS_LABELS } from "../utils";

export function PecHeader({
  data,
  profile,
}: {
  data: PecPreparation;
  profile: ConsolidatedClientProfile | null;
}) {
  return (
    <div className="rounded-xl border border-border bg-white shadow-sm p-5 mb-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <StatusBadge status={data.status} label={STATUS_LABELS[data.status]} />
          {data.devis_id && (
            <span className="text-sm text-gray-500">Devis #{data.devis_id}</span>
          )}
        </div>
        <div className="flex items-center gap-4">
          {data.errors_count > 0 && (
            <span className="inline-flex items-center gap-1 text-sm font-medium text-red-700">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              {data.errors_count} erreur{data.errors_count > 1 ? "s" : ""}
            </span>
          )}
          {data.warnings_count > 0 && (
            <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-700">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              {data.warnings_count} alerte{data.warnings_count > 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
      <div className="mt-4">
        <p className="text-xs font-medium text-gray-500 mb-1">Score de completude</p>
        <CompletionGauge score={data.completude_score} />
      </div>
      {profile && profile.champs_manquants.length > 0 && (
        <p className="mt-3 text-xs text-gray-500">
          Champs manquants : {profile.champs_manquants.join(", ")}
        </p>
      )}
    </div>
  );
}
