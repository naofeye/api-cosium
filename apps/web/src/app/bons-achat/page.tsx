"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { VoucherCard } from "@/components/ui/VoucherCard";
import { Tag, Search } from "lucide-react";

interface Advantage {
  cosium_id: number | null;
  name: string | null;
  description: string | null;
  valid_from: string | null;
  valid_to: string | null;
}

export default function BonsAchatPage() {
  const [operationIdInput, setOperationIdInput] = useState("");
  const [appliedId, setAppliedId] = useState<number | null>(null);

  const { data, error, isLoading } = useSWR<Advantage[]>(
    appliedId ? `/cosium/commercial-operations/${appliedId}/advantages` : null,
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = parseInt(operationIdInput, 10);
    if (!Number.isFinite(parsed) || parsed <= 0) return;
    setAppliedId(parsed);
  };

  const sortedByExpiration = data
    ? [...data].sort((a, b) => {
        const ad = a.valid_to ? new Date(a.valid_to).getTime() : Infinity;
        const bd = b.valid_to ? new Date(b.valid_to).getTime() : Infinity;
        return ad - bd;
      })
    : [];

  return (
    <PageLayout
      title="Bons d'achat"
      description="Avantages des operations commerciales Cosium (lecture seule)"
      breadcrumb={[{ label: "Bons d'achat" }]}
    >
      <div className="rounded-xl border border-border bg-bg-card p-6 mb-6 shadow-sm">
        <form onSubmit={handleSubmit} className="flex items-end gap-3">
          <div className="flex-1 max-w-sm">
            <label
              htmlFor="op-id"
              className="mb-1 block text-sm font-medium text-text-primary"
            >
              Identifiant operation commerciale Cosium
            </label>
            <input
              id="op-id"
              type="number"
              min="1"
              value={operationIdInput}
              onChange={(e) => setOperationIdInput(e.target.value)}
              placeholder="ex: 12345"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
            />
          </div>
          <Button type="submit" disabled={!operationIdInput.trim()}>
            <Search className="h-4 w-4" /> Charger
          </Button>
        </form>
        <p className="mt-3 text-xs text-text-secondary">
          L&apos;API Cosium n&apos;expose que la consultation par operation. Pour
          recuperer l&apos;identifiant d&apos;une operation, consultez votre
          interface Cosium.
        </p>
      </div>

      {appliedId && (
        <div>
          {isLoading && <LoadingState text={`Chargement des avantages pour l'operation #${appliedId}...`} />}
          {error && (
            <ErrorState
              message={error instanceof Error ? error.message : "Erreur de chargement."}
              onRetry={() => setAppliedId(appliedId)}
            />
          )}
          {!isLoading && !error && data && data.length === 0 && (
            <EmptyState
              title="Aucun avantage"
              description={`L'operation #${appliedId} n'a aucun avantage configure dans Cosium.`}
            />
          )}
          {!isLoading && !error && sortedByExpiration.length > 0 && (
            <>
              <h2 className="text-lg font-semibold text-text-primary mb-3 flex items-center gap-2">
                <Tag className="h-4 w-4 text-text-secondary" />
                {sortedByExpiration.length} avantage{sortedByExpiration.length > 1 ? "s" : ""} pour l&apos;operation #{appliedId}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sortedByExpiration.map((adv) => (
                  <VoucherCard
                    key={adv.cosium_id ?? Math.random()}
                    code={adv.cosium_id?.toString() ?? "-"}
                    amount={adv.description ?? adv.name ?? "Avantage"}
                    expiresAt={adv.valid_to}
                    label={adv.name ?? "Avantage"}
                  />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </PageLayout>
  );
}
