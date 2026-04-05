"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { formatMoney } from "@/lib/format";
import { FileText, Euro, CheckCircle, AlertCircle } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { TabResume } from "./tabs/TabResume";
import { TabDocuments } from "./tabs/TabDocuments";
import { TabFinances } from "./tabs/TabFinances";
import { TabIA } from "./tabs/TabIA";
import type { CaseDetail, CaseDocument, PaymentSummary, CompletenessData, Tab } from "./tabs/types";

export default function CaseDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [activeTab, setActiveTab] = useState<Tab>("resume");

  const {
    data: caseData,
    error: caseError,
    isLoading: caseLoading,
    mutate: mutateCase,
  } = useSWR<CaseDetail>(`/cases/${id}`);
  const { data: documents = [], isLoading: docsLoading } = useSWR<CaseDocument[]>(`/cases/${id}/documents`);
  const { data: payments, isLoading: paymentsLoading } = useSWR<PaymentSummary>(`/cases/${id}/payments`);
  const { data: completeness } = useSWR<CompletenessData>(`/cases/${id}/completeness`);

  const isLoading = caseLoading || docsLoading || paymentsLoading;
  const error = caseError?.message ?? null;

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: "..." }]}>
        <LoadingState text="Chargement du dossier..." />
      </PageLayout>
    );
  }

  if (caseError?.message?.includes("introuvable") || caseError?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: "Introuvable" }]}>
        <EmptyState
          title="Dossier introuvable"
          description="Ce dossier n'existe pas ou a ete supprime."
          action={
            <Link href="/cases">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  if (error || !caseData || !payments) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: "Erreur" }]}>
        <ErrorState message={error || "Dossier introuvable"} onRetry={() => mutateCase()} />
      </PageLayout>
    );
  }

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "resume", label: "Resume" },
    { key: "documents", label: "Documents", count: documents.length },
    { key: "finances", label: "Finances" },
    { key: "ia", label: "Assistant IA" },
  ];

  return (
    <PageLayout
      title={`Dossier #${caseData.id} — ${caseData.customer_name}`}
      breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: `#${caseData.id}` }]}
      actions={<StatusBadge status={caseData.status} />}
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={FileText} label="Documents" value={documents.length} color="info" />
        <KPICard icon={Euro} label="Total facture" value={formatMoney(payments.total_due)} color="primary" />
        <KPICard icon={CheckCircle} label="Encaisse" value={formatMoney(payments.total_paid)} color="success" />
        <KPICard
          icon={AlertCircle}
          label="Reste du"
          value={formatMoney(payments.remaining)}
          color={payments.remaining > 0 ? "danger" : "success"}
        />
      </div>

      <div className="border-b border-border mb-6">
        <div className="flex gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary hover:border-gray-300"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{tab.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "resume" && <TabResume caseData={caseData} completeness={completeness ?? null} />}
      {activeTab === "documents" && <TabDocuments documents={documents} />}
      {activeTab === "finances" && <TabFinances payments={payments} />}
      {activeTab === "ia" && <TabIA caseId={caseData.id} />}
    </PageLayout>
  );
}
