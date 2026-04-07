import { KPICard } from "@/components/ui/KPICard";
import { EmptyState } from "@/components/ui/EmptyState";
import type { BatchSummary } from "@/lib/types";
import {
  Users,
  CheckCircle,
  AlertTriangle,
  AlertOctagon,
  XCircle,
  Play,
} from "lucide-react";

interface BatchOverviewStepProps {
  batchSummary: BatchSummary;
  processing: boolean;
  onProcess: () => void;
  onBack: () => void;
}

export function BatchOverviewStep({
  batchSummary,
  processing,
  onProcess,
  onBack,
}: BatchOverviewStepProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <KPICard icon={Users} label="Total clients" value={batchSummary.batch.total_clients} color="info" />
        <KPICard icon={CheckCircle} label="Prets" value={batchSummary.batch.clients_prets} color="success" />
        <KPICard icon={AlertTriangle} label="Incomplets" value={batchSummary.batch.clients_incomplets} color="warning" />
        <KPICard icon={AlertOctagon} label="En conflit" value={batchSummary.batch.clients_en_conflit} color="danger" />
        <KPICard icon={XCircle} label="Erreurs" value={batchSummary.batch.clients_erreur} />
      </div>

      {batchSummary.items.length === 0 ? (
        <EmptyState
          title="Aucun client trouve"
          description="Aucun client trouve pour ce code marketing."
        />
      ) : (
        <div className="flex gap-3">
          <button
            onClick={onProcess}
            disabled={processing}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="h-4 w-4" aria-hidden="true" />
            {processing ? "Traitement en cours..." : "Lancer le traitement"}
          </button>
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-white px-4 py-2 text-sm font-medium text-text-primary hover:bg-gray-50 transition-colors"
          >
            Retour
          </button>
        </div>
      )}
    </div>
  );
}
