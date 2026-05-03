"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { fetchJson } from "@/lib/api";
import { mutateJson } from "@/lib/mutate";
import { formatMoney } from "@/lib/format";
import { factureCreateSchema } from "@/lib/schemas/facture";
import { Euro, FileText, ShieldCheck, Heart, XCircle } from "lucide-react";

import type { DevisDetail } from "./components/DevisTimeline";
import { DevisTimeline } from "./components/DevisTimeline";
import { DevisFinancialSummary } from "./components/DevisFinancialSummary";
import { DevisLinesTable } from "./components/DevisLinesTable";
import { DevisActionButtons } from "./components/DevisActionButtons";

export default function DevisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: devis, error: swrError, isLoading, mutate } = useSWR<DevisDetail>(`/devis/${id}`);
  const [changing, setChanging] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmRefuse, setConfirmRefuse] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const changeStatus = async (newStatus: string) => {
    if (changing) return;
    setChanging(true);
    setMutationError(null);
    try {
      await fetchJson<DevisDetail>(`/devis/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      mutate();
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setChanging(false);
    }
  };

  const generateFacture = async () => {
    if (generating) return;
    setGenerating(true);
    setMutationError(null);
    try {
      const payload = factureCreateSchema.parse({ devis_id: devis!.id });
      // Cle d'idempotence stable : le devis_id sert de cle naturelle
      // pour eviter les doublons de facture sur double-clic / retry.
      const resp = await mutateJson<{ id: number }>("/factures", {
        method: "POST",
        body: JSON.stringify(payload),
        idempotencyKey: `facture-from-devis-${devis!.id}`,
      });
      router.push(`/factures/${resp.id}`);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la generation");
      setGenerating(false);
    }
  };

  const duplicateDevis = async () => {
    if (duplicating || !devis) return;
    setDuplicating(true);
    setMutationError(null);
    try {
      const resp = await fetchJson<{ id: number }>(`/devis/${devis.id}/duplicate`, {
        method: "POST",
      });
      router.push(`/devis/${resp.id}`);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la duplication");
      setDuplicating(false);
    }
  };

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "..." }]}>
        <LoadingState text="Chargement du devis..." />
      </PageLayout>
    );
  }

  if (swrError?.message?.includes("introuvable") || swrError?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Introuvable" }]}>
        <EmptyState
          title="Devis introuvable"
          description="Ce devis n'existe pas ou a ete supprime."
          action={
            <Link href="/devis">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  const error = swrError?.message ?? mutationError ?? null;

  if (error && !devis) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Erreur" }]}>
        <ErrorState message={error || "Devis introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );
  }

  if (!devis) return null;

  return (
    <PageLayout
      title={`Devis ${devis.numero}`}
      breadcrumb={[{ label: "Devis", href: "/devis" }, { label: devis.numero }]}
      actions={
        <DevisActionButtons
          devis={devis}
          changing={changing}
          generating={generating}
          duplicating={duplicating}
          onChangeStatus={changeStatus}
          onGenerateFacture={generateFacture}
          onDuplicate={duplicateDevis}
          onConfirmCancel={() => setConfirmCancel(true)}
          onConfirmRefuse={() => setConfirmRefuse(true)}
        />
      }
    >
      {mutationError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center gap-2">
          <XCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" /> {mutationError}
        </div>
      )}

      <DevisTimeline devis={devis} />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={Euro} label="Total TTC" value={formatMoney(devis.montant_ttc)} color="primary" />
        <KPICard icon={ShieldCheck} label="Part Secu" value={formatMoney(devis.part_secu)} color="info" />
        <KPICard icon={Heart} label="Part Mutuelle" value={formatMoney(devis.part_mutuelle)} color="info" />
        <KPICard
          icon={FileText}
          label="Reste a charge"
          value={formatMoney(devis.reste_a_charge)}
          color={devis.reste_a_charge > 0 ? "danger" : "success"}
        />
      </div>

      <DevisFinancialSummary devis={devis} />
      <DevisLinesTable devis={devis} />

      <ConfirmDialog
        open={confirmCancel}
        title="Annuler ce devis"
        message="Etes-vous sur de vouloir annuler ce devis ? Cette action est irreversible."
        confirmLabel="Annuler le devis"
        danger
        onConfirm={() => {
          setConfirmCancel(false);
          changeStatus("annule");
        }}
        onCancel={() => setConfirmCancel(false)}
      />
      <ConfirmDialog
        open={confirmRefuse}
        title="Marquer comme refuse"
        message="Confirmer le refus de ce devis par le client ? Vous pourrez dupliquer le devis pour creer une nouvelle proposition."
        confirmLabel="Marquer comme refuse"
        danger
        onConfirm={() => {
          setConfirmRefuse(false);
          changeStatus("refuse");
        }}
        onCancel={() => setConfirmRefuse(false)}
      />
    </PageLayout>
  );
}
