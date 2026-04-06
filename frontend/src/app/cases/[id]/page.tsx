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
import { FileText, Euro, CheckCircle, AlertCircle, PlusCircle, Activity, Upload } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { TabResume } from "./tabs/TabResume";
import { TabDocuments } from "./tabs/TabDocuments";
import { TabFinances } from "./tabs/TabFinances";
import { TabIA } from "./tabs/TabIA";
import { TabHistorique } from "./tabs/TabHistorique";
import type { CaseDetail, CaseDocument, PaymentSummary, CompletenessData, CaseActivity, Tab } from "./tabs/types";

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
  const { data: activities = [] } = useSWR<CaseActivity[]>(`/cases/${id}/activities`);

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

  const completenessScore = completeness && completeness.total_required > 0
    ? Math.round((completeness.total_present / completeness.total_required) * 100)
    : completeness ? 100 : null;

  const missingDocs = completeness
    ? completeness.items.filter((item) => !item.present && item.is_required)
    : [];

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "resume", label: "Resume" },
    { key: "documents", label: "Documents", count: documents.length },
    { key: "finances", label: "Finances" },
    { key: "historique", label: "Historique", count: activities.length },
    { key: "ia", label: "Assistant IA" },
  ];

  return (
    <PageLayout
      title={`Dossier #${caseData.id} — ${caseData.customer_name}`}
      breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: `#${caseData.id}` }]}
      actions={
        <div className="flex items-center gap-3">
          {completenessScore !== null && (
            <div className="flex items-center gap-2" title={`Completude : ${completenessScore}%`}>
              <div className="relative h-8 w-8">
                <svg className="h-8 w-8 -rotate-90" viewBox="0 0 36 36">
                  <circle
                    cx="18" cy="18" r="15.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    className="text-gray-200"
                  />
                  <circle
                    cx="18" cy="18" r="15.5"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="3"
                    strokeDasharray={`${completenessScore} ${100 - completenessScore}`}
                    strokeLinecap="round"
                    className={completenessScore === 100 ? "text-emerald-500" : completenessScore >= 50 ? "text-amber-500" : "text-red-500"}
                  />
                </svg>
                <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-text-primary">
                  {completenessScore}%
                </span>
              </div>
            </div>
          )}
          <StatusBadge status={caseData.status} />
        </div>
      }
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

      {/* Quick-add buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        <Link href={`/devis/new?case_id=${caseData.id}`}>
          <Button variant="outline" size="sm">
            <PlusCircle className="h-4 w-4 mr-1" /> Nouveau devis
          </Button>
        </Link>
        <Link href={`/pec/new?case_id=${caseData.id}`}>
          <Button variant="outline" size="sm">
            <PlusCircle className="h-4 w-4 mr-1" /> Nouvelle PEC
          </Button>
        </Link>
        <Link href={`/cases/${caseData.id}/documents/upload`}>
          <Button variant="outline" size="sm">
            <Upload className="h-4 w-4 mr-1" /> Ajouter document
          </Button>
        </Link>
      </div>

      {/* Missing documents alert */}
      {missingDocs.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-6">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-4 w-4 text-amber-600" />
            <span className="text-sm font-semibold text-amber-800">
              {missingDocs.length} piece{missingDocs.length > 1 ? "s" : ""} manquante{missingDocs.length > 1 ? "s" : ""}
            </span>
          </div>
          <div className="flex flex-wrap gap-2">
            {missingDocs.map((doc) => (
              <Link key={doc.code} href={`/cases/${caseData.id}/documents/upload?type=${doc.code}`}>
                <Button variant="outline" size="sm" className="text-amber-700 border-amber-300 hover:bg-amber-100">
                  <PlusCircle className="h-3.5 w-3.5 mr-1" /> {doc.label}
                </Button>
              </Link>
            ))}
          </div>
        </div>
      )}

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
      {activeTab === "historique" && <TabHistorique activities={activities} />}
      {activeTab === "ia" && <TabIA caseId={caseData.id} />}
    </PageLayout>
  );
}
