"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { ShieldCheck, Plus, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { CompletionGauge } from "@/components/pec/CompletionGauge";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import type { PecPreparationSummary } from "@/lib/types/pec-preparation";

interface TabPECProps {
  clientId: string | number;
}

const STATUS_LABELS: Record<string, string> = {
  en_preparation: "En preparation",
  prete: "Prete",
  soumise: "Soumise",
  archivee: "Archivee",
};

export function TabPEC({ clientId }: TabPECProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [creating, setCreating] = useState(false);

  const { data, error, isLoading, mutate } = useSWR<PecPreparationSummary[]>(
    `/clients/${clientId}/pec-preparations`,
  );

  const handleCreate = async () => {
    setCreating(true);
    try {
      const result = await fetchJson<{ id: number }>(`/clients/${clientId}/pec-preparation`, {
        method: "POST",
        body: JSON.stringify({ devis_id: null }),
      });
      toast("Preparation PEC creee avec succes", "success");
      mutate();
      router.push(`/clients/${clientId}/pec-preparation/${result.id}`);
    } catch (e) {
      toast(e instanceof Error ? e.message : "Impossible de creer la preparation PEC", "error");
    } finally {
      setCreating(false);
    }
  };

  if (isLoading) {
    return <LoadingState text="Chargement des preparations PEC..." />;
  }

  if (error) {
    return (
      <ErrorState
        message={error.message ?? "Impossible de charger les preparations PEC."}
        onRetry={() => mutate()}
      />
    );
  }

  const preparations = data ?? [];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">Assistance PEC</h3>
        <Button onClick={handleCreate} loading={creating}>
          <Plus className="h-4 w-4 mr-1" /> Nouvelle assistance PEC
        </Button>
      </div>

      {preparations.length === 0 ? (
        <EmptyState
          title="Aucune preparation PEC"
          description="Creez votre premiere assistance PEC pour ce client."
          icon={ShieldCheck}
          action={
            <Button onClick={handleCreate} loading={creating}>
              <Plus className="h-4 w-4 mr-1" /> Creer une assistance PEC
            </Button>
          }
        />
      ) : (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50">
                <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">ID</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Completude</th>
                <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Erreurs</th>
                <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Alertes</th>
                <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
              </tr>
            </thead>
            <tbody>
              {preparations.map((p) => (
                <tr
                  key={p.id}
                  className="border-b last:border-0 cursor-pointer hover:bg-gray-50 transition-colors"
                  onClick={() => router.push(`/clients/${clientId}/pec-preparation/${p.id}`)}
                >
                  <td className="px-4 py-3 font-mono">#{p.id}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} label={STATUS_LABELS[p.status]} />
                  </td>
                  <td className="px-4 py-3 w-48">
                    <CompletionGauge score={p.completude_score} />
                  </td>
                  <td className="px-4 py-3 text-center">
                    {p.errors_count > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-red-100 text-red-700 px-2 py-0.5 text-xs font-medium">
                        {p.errors_count}
                      </span>
                    ) : (
                      <span className="text-gray-400">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-center">
                    {p.warnings_count > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-xs font-medium">
                        {p.warnings_count}
                      </span>
                    ) : (
                      <span className="text-gray-400">0</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {p.created_at ? <DateDisplay date={p.created_at} /> : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
