"use client";

import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import type { CosiumDataBundle } from "../types";

import { TabResume } from "../tabs/TabResume";
import { TabDossiers } from "../tabs/TabDossiers";
import { TabFinances } from "../tabs/TabFinances";
import { TabDocuments } from "../tabs/TabDocuments";
import { TabMarketing } from "../tabs/TabMarketing";
import { TabHistorique } from "../tabs/TabHistorique";
import { TabCosiumDocuments } from "../tabs/TabCosiumDocuments";
import { TabOrdonnances } from "../tabs/TabOrdonnances";
import { TabCosiumPaiements } from "../tabs/TabCosiumPaiements";
import { TabRendezVous } from "../tabs/TabRendezVous";
import { TabEquipements } from "../tabs/TabEquipements";

export type Tab =
  | "resume"
  | "dossiers"
  | "finances"
  | "documents"
  | "marketing"
  | "historique"
  | "cosium-docs"
  | "ordonnances"
  | "cosium-paiements"
  | "rendez-vous"
  | "equipements";

interface TabDef {
  key: Tab;
  label: string;
  count?: number;
}

interface ClientTabsProps {
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
  cosiumId: string | number | null;
  cosiumData: CosiumDataBundle | null;
  dossiers: { id: number; statut: string; source: string; created_at: string }[];
  devis: { id: number; numero: string; statut: string; montant_ttc: number; reste_a_charge: number }[];
  factures: { id: number; numero: string; statut: string; montant_ttc: number; date_emission: string }[];
  paiements: { id: number; payeur: string; mode: string | null; montant_du: number; montant_paye: number; statut: string }[];
  documents: { id: number; type: string; filename: string; uploaded_at: string }[];
  consentements: { canal: string; consenti: boolean }[];
  interactions: { id: number; type: string; direction: string; subject: string; content: string | null; created_at: string }[];
  cosiumInvoices: { cosium_id: number; invoice_number: string; invoice_date: string | null; type: string; total_ti: number; outstanding_balance: number; share_social_security: number; share_private_insurance: number; settled: boolean }[];
  // Resume tab props
  firstName: string;
  lastName: string;
  phone: string | null;
  email: string | null;
  socialSecurityNumber: string | null;
  postalCode: string | null;
  city: string | null;
  renewalEligible: boolean;
  renewalMonths: number;
  // Historique form state
  showForm: boolean;
  onShowForm: (v: boolean) => void;
  intType: string;
  onIntTypeChange: (v: string) => void;
  intDir: string;
  onIntDirChange: (v: string) => void;
  intSubj: string;
  onIntSubjChange: (v: string) => void;
  intBody: string;
  onIntBodyChange: (v: string) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

export function ClientTabs({
  activeTab,
  onTabChange,
  cosiumId,
  cosiumData: cd,
  dossiers,
  devis,
  factures,
  paiements,
  documents,
  consentements,
  interactions,
  cosiumInvoices,
  firstName,
  lastName,
  phone,
  email,
  socialSecurityNumber,
  postalCode,
  city,
  renewalEligible,
  renewalMonths,
  showForm,
  onShowForm,
  intType,
  onIntTypeChange,
  intDir,
  onIntDirChange,
  intSubj,
  onIntSubjChange,
  intBody,
  onIntBodyChange,
  submitting,
  onSubmit,
}: ClientTabsProps) {
  const tabs: TabDef[] = [
    { key: "resume", label: "Resume" },
    { key: "dossiers", label: "Dossiers", count: dossiers?.length ?? 0 },
    { key: "finances", label: "Finances", count: factures?.length ?? 0 },
    { key: "documents", label: "Documents", count: documents?.length ?? 0 },
    { key: "ordonnances", label: "Ordonnances", count: cd?.prescriptions?.length ?? 0 },
    { key: "cosium-paiements", label: "Paiements Cosium", count: cd?.cosium_payments?.length ?? 0 },
    { key: "rendez-vous", label: "Rendez-vous", count: cd?.calendar_events?.length ?? 0 },
    { key: "equipements", label: "Equipements", count: cd?.equipments?.length ?? 0 },
    ...(cosiumId ? [{ key: "cosium-docs" as Tab, label: "Docs Cosium" }] : []),
    { key: "marketing", label: "Marketing" },
    { key: "historique", label: "Historique", count: interactions?.length ?? 0 },
  ];

  return (
    <>
      {/* Tabs navigation */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-0 overflow-x-auto" role="tablist" aria-label="Sections du client">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={activeTab === t.key}
              aria-controls={`tabpanel-${t.key}`}
              id={`tab-${t.key}`}
              onClick={() => onTabChange(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${activeTab === t.key ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"}`}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab panels */}
      {activeTab === "resume" && (
        <ErrorBoundary name="TabResume">
          <TabResume
            firstName={firstName}
            lastName={lastName}
            phone={phone}
            email={email}
            socialSecurityNumber={socialSecurityNumber}
            postalCode={postalCode}
            city={city}
            renewalEligible={renewalEligible}
            renewalMonths={renewalMonths}
            interactions={interactions}
            correction={cd?.correction_actuelle ?? null}
            totalCaCosium={cd?.total_ca_cosium ?? 0}
            lastVisitDate={cd?.last_visit_date ?? null}
            nextRdv={cd?.calendar_events?.find((ev) => !ev.canceled && ev.start_date && new Date(ev.start_date) > new Date()) ?? null}
            cosiumInvoices={cosiumInvoices}
            mutuelles={cd?.mutuelles ?? []}
          />
        </ErrorBoundary>
      )}
      {activeTab === "dossiers" && (
        <ErrorBoundary name="TabDossiers">
          <TabDossiers dossiers={dossiers} />
        </ErrorBoundary>
      )}
      {activeTab === "finances" && (
        <ErrorBoundary name="TabFinances">
          <TabFinances
            devis={devis}
            factures={factures}
            paiements={paiements}
            cosiumInvoices={cosiumInvoices}
          />
        </ErrorBoundary>
      )}
      {activeTab === "documents" && (
        <ErrorBoundary name="TabDocuments">
          <TabDocuments documents={documents} />
        </ErrorBoundary>
      )}
      {activeTab === "marketing" && (
        <ErrorBoundary name="TabMarketing">
          <TabMarketing consentements={consentements} />
        </ErrorBoundary>
      )}
      {activeTab === "cosium-docs" && (
        <ErrorBoundary name="TabCosiumDocuments">
          <TabCosiumDocuments cosiumId={cosiumId} />
        </ErrorBoundary>
      )}
      {activeTab === "ordonnances" && (
        <ErrorBoundary name="TabOrdonnances">
          <TabOrdonnances prescriptions={cd?.prescriptions ?? []} />
        </ErrorBoundary>
      )}
      {activeTab === "cosium-paiements" && (
        <ErrorBoundary name="TabCosiumPaiements">
          <TabCosiumPaiements payments={cd?.cosium_payments ?? []} />
        </ErrorBoundary>
      )}
      {activeTab === "rendez-vous" && (
        <ErrorBoundary name="TabRendezVous">
          <TabRendezVous events={cd?.calendar_events ?? []} />
        </ErrorBoundary>
      )}
      {activeTab === "equipements" && (
        <ErrorBoundary name="TabEquipements">
          <TabEquipements equipments={cd?.equipments ?? []} />
        </ErrorBoundary>
      )}
      {activeTab === "historique" && (
        <ErrorBoundary name="TabHistorique">
          <TabHistorique
            interactions={interactions}
            showForm={showForm}
            onShowForm={onShowForm}
            intType={intType}
            onIntTypeChange={onIntTypeChange}
            intDir={intDir}
            onIntDirChange={onIntDirChange}
            intSubj={intSubj}
            onIntSubjChange={onIntSubjChange}
            intBody={intBody}
            onIntBodyChange={onIntBodyChange}
            submitting={submitting}
            onSubmit={onSubmit}
          />
        </ErrorBoundary>
      )}
    </>
  );
}
