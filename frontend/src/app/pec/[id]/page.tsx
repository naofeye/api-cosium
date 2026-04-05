"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { Euro, Shield } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";
import { TabHistorique, HistoryItem } from "./tabs/TabHistorique";
import { TabRelances, RelanceItem } from "./tabs/TabRelances";

interface PecDetail {
  id: number;
  case_id: number;
  organization_id: number;
  facture_id: number | null;
  montant_demande: number;
  montant_accorde: number | null;
  status: string;
  created_at: string;
  organization_name: string | null;
  customer_name: string | null;
  history: HistoryItem[];
}

const NEXT_STATUSES: Record<string, { label: string; status: string; variant: "primary" | "outline" | "danger" }[]> = {
  soumise: [
    { label: "En attente", status: "en_attente", variant: "outline" },
    { label: "Accepter", status: "acceptee", variant: "primary" },
    { label: "Refuser", status: "refusee", variant: "danger" },
  ],
  en_attente: [
    { label: "Accepter", status: "acceptee", variant: "primary" },
    { label: "Partielle", status: "partielle", variant: "outline" },
    { label: "Refuser", status: "refusee", variant: "danger" },
  ],
  acceptee: [{ label: "Cloturer", status: "cloturee", variant: "outline" }],
  refusee: [{ label: "Cloturer", status: "cloturee", variant: "outline" }],
  partielle: [{ label: "Cloturer", status: "cloturee", variant: "outline" }],
  cloturee: [],
};

export default function PecDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const { data: pec, error: pecError, isLoading: pecLoading, mutate: mutatePec } = useSWR<PecDetail>(`/pec/${id}`);
  const { data: relances = [], mutate: mutateRelances } = useSWR<RelanceItem[]>(`/pec/${id}/relances`);

  const [changing, setChanging] = useState(false);
  const [montantAccorde, setMontantAccorde] = useState("");
  const [comment, setComment] = useState("");
  const [relanceType, setRelanceType] = useState("email");
  const [relanceContenu, setRelanceContenu] = useState("");
  const [submittingRelance, setSubmittingRelance] = useState(false);
  const [activeTab, setActiveTab] = useState<"historique" | "relances">("historique");
  const [mutationError, setMutationError] = useState<string | null>(null);

  const changeStatus = async (newStatus: string) => {
    if (changing) return;
    setChanging(true);
    try {
      const body: Record<string, unknown> = { status: newStatus };
      if (montantAccorde) body.montant_accorde = Number(montantAccorde);
      if (comment) body.comment = comment;
      await fetchJson(`/pec/${id}/status`, { method: "PATCH", body: JSON.stringify(body) });
      setComment("");
      setMontantAccorde("");
      mutatePec();
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setChanging(false);
    }
  };

  const addRelance = async () => {
    if (submittingRelance) return;
    setSubmittingRelance(true);
    try {
      await fetchJson(`/pec/${id}/relances`, {
        method: "POST",
        body: JSON.stringify({ type: relanceType, contenu: relanceContenu || null }),
      });
      setRelanceContenu("");
      mutateRelances();
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setSubmittingRelance(false);
    }
  };

  const isLoading = pecLoading;
  const error = pecError?.message ?? mutationError ?? null;

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "PEC", href: "/pec" }, { label: "..." }]}>
        <LoadingState text="Chargement de la PEC..." />
      </PageLayout>
    );
  }

  if (pecError?.message?.includes("introuvable") || pecError?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "PEC", href: "/pec" }, { label: "Introuvable" }]}>
        <EmptyState
          title="PEC introuvable"
          description="Cette prise en charge n'existe pas ou a ete supprimee."
          action={
            <Link href="/pec">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  if (error || !pec) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "PEC", href: "/pec" }, { label: "Erreur" }]}>
        <ErrorState message={error || "PEC introuvable"} onRetry={() => mutatePec()} />
      </PageLayout>
    );
  }

  const actions = NEXT_STATUSES[pec.status] || [];

  return (
    <PageLayout
      title={`PEC #${pec.id}`}
      breadcrumb={[{ label: "PEC", href: "/pec" }, { label: `#${pec.id}` }]}
      actions={<StatusBadge status={pec.status} />}
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <KPICard icon={Euro} label="Montant demande" value={formatMoney(pec.montant_demande)} color="primary" />
        <KPICard
          icon={Shield}
          label="Montant accorde"
          value={pec.montant_accorde !== null ? formatMoney(pec.montant_accorde) : "-"}
          color={pec.montant_accorde !== null ? "success" : "info"}
        />
        <KPICard
          icon={Euro}
          label="Ecart"
          value={pec.montant_accorde !== null ? formatMoney(pec.montant_demande - pec.montant_accorde) : "-"}
          color={pec.montant_accorde !== null && pec.montant_accorde < pec.montant_demande ? "danger" : "success"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Informations</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Client</span>
              <span className="font-medium">{pec.customer_name || "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Organisme</span>
              <span className="font-medium">{pec.organization_name || "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Dossier</span>
              <a href={`/cases/${pec.case_id}`} className="text-primary hover:underline">
                #{pec.case_id}
              </a>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Date</span>
              <DateDisplay date={pec.created_at} />
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Actions</h3>
          {actions.length === 0 ? (
            <p className="text-sm text-text-secondary">Cette PEC est cloturee.</p>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">Montant accorde</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={montantAccorde}
                    onChange={(e) => setMontantAccorde(e.target.value)}
                    placeholder="Optionnel"
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text-primary mb-1">Commentaire</label>
                  <input
                    type="text"
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Optionnel"
                    className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex gap-2">
                {actions.map((a) => (
                  <Button key={a.status} variant={a.variant} onClick={() => changeStatus(a.status)} disabled={changing}>
                    {a.label}
                  </Button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-b border-border mb-6">
        <div className="flex gap-0">
          {(["historique", "relances"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${
                activeTab === tab
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              {tab} {tab === "relances" ? `(${relances.length})` : `(${pec.history.length})`}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "historique" && <TabHistorique history={pec.history} />}

      {activeTab === "relances" && (
        <TabRelances
          relances={relances}
          relanceType={relanceType}
          onRelanceTypeChange={setRelanceType}
          relanceContenu={relanceContenu}
          onRelanceContenuChange={setRelanceContenu}
          submittingRelance={submittingRelance}
          onAddRelance={addRelance}
        />
      )}
    </PageLayout>
  );
}
