"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { ArrowLeft } from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { AuditTrailModal } from "@/components/pec/AuditTrailModal";
import { PreControlPanel } from "@/components/pec/PreControlPanel";
import { useUnsavedChangesWarning } from "@/hooks/useUnsavedChangesWarning";
import type { PecPreparation, PecPreparationDocument } from "@/lib/types/pec-preparation";

import { CopyPasteSummary } from "./components/CopyPasteSummary";
import { PecActionBar } from "./components/PecActionBar";
import { PecHeader } from "./components/PecHeader";
import { PecSections } from "./components/PecSections";
import { usePecActions } from "./hooks/usePecActions";

export default function PecPreparationDetailPage() {
  const params = useParams();
  const clientId = params.id as string;
  const prepId = params.prepId as string;

  const { data, error, isLoading, mutate } = useSWR<PecPreparation>(
    `/clients/${clientId}/pec-preparation/${prepId}`,
  );
  const { data: documents } = useSWR<PecPreparationDocument[]>(
    `/pec-preparations/${prepId}/documents`,
  );

  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [auditModalOpen, setAuditModalOpen] = useState(false);

  const { state, helpers, actions } = usePecActions({ prepId, data, mutate });

  const hasPendingWork = state.pendingCorrections > 0 && data?.status === "en_preparation";
  useUnsavedChangesWarning(
    hasPendingWork,
    "Vous avez des modifications non enregistrees. Voulez-vous quitter sans sauvegarder ?",
  );

  const breadcrumb = [
    { label: "Clients", href: "/clients" },
    { label: "Client", href: `/clients/${clientId}` },
    { label: data ? `Assistance PEC #${data.id}` : "Assistance PEC" },
  ];

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={breadcrumb}>
        <LoadingState text="Chargement de la preparation PEC..." />
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout title="Erreur" breadcrumb={breadcrumb}>
        <ErrorState
          message={error?.message ?? "Preparation PEC introuvable."}
          onRetry={() => mutate()}
        />
      </PageLayout>
    );
  }

  const profile = data.consolidated_data ?? null;
  const canSubmit = data.errors_count === 0 && data.status === "en_preparation";

  return (
    <PageLayout
      title={`Assistance PEC #${data.id}`}
      breadcrumb={breadcrumb}
      actions={
        <Link href={`/clients/${clientId}`}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" /> Retour
          </Button>
        </Link>
      }
    >
      <PreControlPanel
        preparationId={prepId}
        onOpenAudit={() => setAuditModalOpen(true)}
      />

      <AuditTrailModal
        preparationId={prepId}
        open={auditModalOpen}
        onClose={() => setAuditModalOpen(false)}
      />

      <PecHeader data={data} profile={profile} />

      <PecSections
        data={data}
        profile={profile}
        documents={documents}
        dismissedAlerts={dismissedAlerts}
        onDismissAlert={(key) => setDismissedAlerts((prev) => new Set([...prev, key]))}
        isFieldValidated={helpers.isFieldValidated}
        getOriginalValue={helpers.getOriginalValue}
        getCorrectionReason={helpers.getCorrectionReason}
        onValidate={actions.handleValidate}
        onCorrect={actions.handleCorrect}
        onUndoCorrection={actions.handleUndoCorrection}
      />

      {profile && <CopyPasteSummary profile={profile} />}

      <PecActionBar
        clientId={clientId}
        refreshing={state.refreshing}
        exporting={state.exporting}
        submitting={state.submitting}
        canSubmit={canSubmit}
        onRefresh={actions.handleRefresh}
        onExportPDF={actions.handleExportPDF}
        onSubmit={actions.handleSubmit}
      />
    </PageLayout>
  );
}
