import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import type { MarketingCode } from "@/lib/types";

interface BatchSelectStepProps {
  marketingCodes: MarketingCode[] | undefined;
  codesLoading: boolean;
  codesError: unknown;
  selectedCode: string;
  operationLabel: string;
  creating: boolean;
  onSelectCode: (code: string) => void;
  onChangeLabel: (label: string) => void;
  onCreateBatch: () => void;
}

export function BatchSelectStep({
  marketingCodes,
  codesLoading,
  codesError,
  selectedCode,
  operationLabel,
  creating,
  onSelectCode,
  onChangeLabel,
  onCreateBatch,
}: BatchSelectStepProps) {
  return (
    <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-text-primary mb-4">
        1. Selectionner un code marketing
      </h2>

      {codesLoading && (
        <LoadingState text="Chargement des codes marketing..." />
      )}

      {codesError && (
        <ErrorState
          message="Impossible de charger les codes marketing."
          onRetry={() => window.location.reload()}
        />
      )}

      {!codesLoading && !codesError && marketingCodes && marketingCodes.length === 0 && (
        <EmptyState
          title="Aucun code marketing trouve"
          description="Synchronisez les tags Cosium."
        />
      )}

      {!codesLoading && !codesError && marketingCodes && marketingCodes.length > 0 && (
        <div className="space-y-4">
          <div>
            <label
              htmlFor="marketing-code"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Code marketing
            </label>
            <select
              id="marketing-code"
              value={selectedCode}
              onChange={(e) => onSelectCode(e.target.value)}
              className="w-full max-w-md rounded-lg border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            >
              <option value="">-- Choisir un code --</option>
              {marketingCodes.map((mc) => (
                <option key={mc.code} value={mc.code}>
                  {mc.description || mc.code} ({mc.client_count} clients)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label
              htmlFor="operation-label"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Label de l&apos;operation (optionnel)
            </label>
            <input
              id="operation-label"
              type="text"
              value={operationLabel}
              onChange={(e) => onChangeLabel(e.target.value)}
              placeholder="Journee SAFRAN 06/04/2026"
              className="w-full max-w-md rounded-lg border border-border px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <button
            onClick={onCreateBatch}
            disabled={!selectedCode || creating}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {creating ? "Creation en cours..." : "Creer le lot"}
          </button>
        </div>
      )}
    </div>
  );
}
