"use client";

import { useState, useTransition } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchJson } from "@/lib/api";
import { RefreshCw, Send, Sparkles, Users } from "lucide-react";
import { RenewalKPIs } from "./components/RenewalKPIs";
import type { RenewalDashboard } from "./components/RenewalKPIs";
import { OpportunityTable } from "./components/OpportunityTable";
import type { RenewalOpportunity } from "./components/OpportunityTable";

type Tab = "opportunities" | "campaign";

export default function RenewalsPage() {
  const {
    data: dashboard,
    error: dashErr,
    isLoading: dashLoading,
    mutate: mutateDash,
  } = useSWR<RenewalDashboard>("/renewals/dashboard");
  const {
    data: opportunities,
    error: oppErr,
    isLoading: oppLoading,
    mutate: mutateOpp,
  } = useSWR<RenewalOpportunity[]>("/renewals/opportunities");
  const [activeTab, setActiveTab] = useState<Tab>("opportunities");
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [campaignName, setCampaignName] = useState("");
  const [campaignChannel, setCampaignChannel] = useState("email");
  const [useAi, setUseAi] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState<string | null>(null);
  const [aiPending, startAiTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const isLoading = dashLoading || oppLoading;
  const fetchError = dashErr?.message ?? oppErr?.message ?? null;
  const mutateAll = () => {
    mutateDash();
    mutateOpp();
  };
  const safeOpportunities = opportunities ?? [];

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    if (selected.size === safeOpportunities.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(safeOpportunities.map((o) => o.customer_id)));
    }
  };

  const selectHighScore = () => {
    setSelected(new Set(safeOpportunities.filter((o) => o.score >= 70).map((o) => o.customer_id)));
  };

  const handleCreateCampaign = async () => {
    if (!campaignName.trim() || selected.size === 0) return;
    setSubmitting(true);
    try {
      await fetchJson("/renewals/campaign", {
        method: "POST",
        body: JSON.stringify({
          name: campaignName,
          channel: campaignChannel,
          customer_ids: Array.from(selected),
          use_ai_message: useAi,
        }),
      });
      setCampaignName("");
      setSelected(new Set());
      setActiveTab("opportunities");
      mutateAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur inconnue";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleAiAnalysis = () => {
    startAiTransition(async () => {
      try {
        const res = await fetchJson<{ analysis: string }>("/renewals/ai-analysis");
        setAiAnalysis(res.analysis);
      } catch {
        setAiAnalysis("Impossible de generer l'analyse IA. Verifiez la configuration.");
      }
    });
  };

  const displayError = fetchError ?? error;

  if (isLoading)
    return (
      <PageLayout title="Renouvellements">
        <LoadingState text="Chargement des opportunites..." />
      </PageLayout>
    );
  if (displayError)
    return (
      <PageLayout title="Renouvellements">
        <ErrorState
          message={displayError}
          onRetry={() => {
            setError(null);
            mutateAll();
          }}
        />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Copilote Renouvellement"
      description="Detectez et relancez les clients eligibles au renouvellement de leur equipement optique"
      breadcrumb={[{ label: "Renouvellements" }]}
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={mutateAll}>
            <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" /> Actualiser
          </Button>
          <Button onClick={handleAiAnalysis} disabled={aiPending}>
            <Sparkles className="mr-2 h-4 w-4" aria-hidden="true" />
            {aiPending ? "Analyse en cours..." : "Analyse IA"}
          </Button>
        </div>
      }
    >
      {dashboard && <RenewalKPIs dashboard={dashboard} />}

      {aiAnalysis && (
        <div className="mb-6 rounded-xl border border-blue-200 bg-blue-50 p-6">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="h-5 w-5 text-blue-600" aria-hidden="true" />
            <h3 className="font-semibold text-blue-900">Analyse IA du potentiel</h3>
          </div>
          <p className="text-sm text-blue-800 whitespace-pre-line">{aiAnalysis}</p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-4 border-b border-border mb-6">
        <button
          className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "opportunities"
              ? "border-primary text-primary"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
          onClick={() => setActiveTab("opportunities")}
        >
          Opportunites ({safeOpportunities.length})
        </button>
        <button
          className={`pb-3 px-1 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "campaign"
              ? "border-primary text-primary"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
          onClick={() => setActiveTab("campaign")}
        >
          Creer une campagne {selected.size > 0 && `(${selected.size})`}
        </button>
      </div>

      {activeTab === "opportunities" && (
        <OpportunityTable
          opportunities={safeOpportunities}
          selected={selected}
          onToggleSelect={toggleSelect}
          onSelectAll={selectAll}
          onSelectHighScore={selectHighScore}
          onGoToCampaign={() => setActiveTab("campaign")}
        />
      )}

      {activeTab === "campaign" && (
        <div className="max-w-2xl">
          {selected.size === 0 ? (
            <EmptyState
              title="Aucun client selectionne"
              description="Retournez dans l'onglet Opportunites et selectionnez les clients a relancer."
              action={<Button onClick={() => setActiveTab("opportunities")}>Voir les opportunites</Button>}
            />
          ) : (
            <div className="space-y-6">
              <div className="rounded-xl border border-border bg-bg-card p-6">
                <h3 className="text-lg font-semibold mb-4">Nouvelle campagne de renouvellement</h3>
                <div className="space-y-4">
                  <div>
                    <label htmlFor="renewal-campaign-name" className="block text-sm font-medium text-text-primary mb-1">Nom de la campagne *</label>
                    <input
                      id="renewal-campaign-name"
                      type="text"
                      value={campaignName}
                      onChange={(e) => setCampaignName(e.target.value)}
                      placeholder="Ex: Renouvellement avril 2026"
                      className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    />
                  </div>
                  <div>
                    <label htmlFor="renewal-campaign-channel" className="block text-sm font-medium text-text-primary mb-1">Canal</label>
                    <select
                      id="renewal-campaign-channel"
                      value={campaignChannel}
                      onChange={(e) => setCampaignChannel(e.target.value)}
                      className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
                    >
                      <option value="email">Email</option>
                      <option value="sms">SMS</option>
                    </select>
                  </div>
                  <div className="flex items-center gap-2">
                    <input type="checkbox" id="useAi" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} />
                    <label htmlFor="useAi" className="text-sm text-text-primary">
                      <Sparkles className="inline h-4 w-4 mr-1 text-blue-500" aria-hidden="true" />
                      Generer le message avec l&apos;IA
                    </label>
                  </div>
                  <div className="rounded-lg bg-gray-50 p-4 text-sm text-text-secondary">
                    <Users className="inline h-4 w-4 mr-1" aria-hidden="true" />
                    {selected.size} client{selected.size > 1 ? "s" : ""} selectionne{selected.size > 1 ? "s" : ""}
                  </div>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <Button variant="outline" onClick={() => setActiveTab("opportunities")}>
                  Retour
                </Button>
                <Button onClick={handleCreateCampaign} disabled={!campaignName.trim() || submitting}>
                  {submitting ? "Creation en cours..." : "Creer la campagne"}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </PageLayout>
  );
}
