"use client";

import dynamic from "next/dynamic";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { LoadingState } from "@/components/ui/LoadingState";

// Tabs prioritaires (rendu sync — vus en premier)
import { TabResume } from "../tabs/TabResume";
import { TabDossiers } from "../tabs/TabDossiers";
import { TabFinances } from "../tabs/TabFinances";
import { TabDocuments } from "../tabs/TabDocuments";
import { TabOrdonnances } from "../tabs/TabOrdonnances";
import { TabRendezVous } from "../tabs/TabRendezVous";
import { TabEquipements } from "../tabs/TabEquipements";

import { ClientTabsNav } from "./ClientTabsNav";
import type { Tab, TabDef, ClientTabsProps } from "./ClientTabsTypes";

// Re-export Tab type for consumers
export type { Tab };

// Tabs secondaires (lazy-loaded → reduction bundle initial).
// Next.js exige que le 2e argument de `dynamic()` soit un object literal (pas une reference).
const TabMarketing = dynamic(() => import("../tabs/TabMarketing").then((m) => m.TabMarketing), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabHistorique = dynamic(() => import("../tabs/TabHistorique").then((m) => m.TabHistorique), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabCosiumDocuments = dynamic(() => import("../tabs/TabCosiumDocuments").then((m) => m.TabCosiumDocuments), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabCosiumPaiements = dynamic(() => import("../tabs/TabCosiumPaiements").then((m) => m.TabCosiumPaiements), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabFidelite = dynamic(() => import("../tabs/TabFidelite").then((m) => m.TabFidelite), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabPEC = dynamic(() => import("../tabs/TabPEC").then((m) => m.TabPEC), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabActivite = dynamic(() => import("../tabs/TabActivite").then((m) => m.TabActivite), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabRapprochement = dynamic(() => import("../tabs/TabRapprochement").then((m) => m.TabRapprochement), {
  loading: () => <LoadingState text="Chargement..." />,
});
const TabSAV = dynamic(() => import("../tabs/TabSAV").then((m) => m.TabSAV), {
  loading: () => <LoadingState text="Chargement..." />,
});

export function ClientTabs({
  activeTab,
  onTabChange,
  clientId,
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
  onDataRefresh,
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
    ...(cosiumId ? [{ key: "fidelite" as Tab, label: "Fidelite" }] : []),
    ...(cosiumId ? [{ key: "sav" as Tab, label: "SAV" }] : []),
    ...(cosiumId ? [{ key: "cosium-docs" as Tab, label: "Docs Cosium" }] : []),
    { key: "rapprochement" as Tab, label: "Rapprochement" },
    { key: "pec" as Tab, label: "Assistance PEC" },
    { key: "activite" as Tab, label: "Activite" },
    { key: "marketing", label: "Marketing" },
    { key: "historique", label: "Historique", count: interactions?.length ?? 0 },
  ];

  return (
    <>
      <ClientTabsNav tabs={tabs} activeTab={activeTab} onTabChange={onTabChange} />

      {/* Tab panels */}
      {activeTab === "resume" && (
        <ErrorBoundary name="TabResume">
          <TabResume
            clientId={clientId}
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
            onNoteAdded={onDataRefresh}
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
          <TabEquipements equipments={cd?.equipments ?? []} cosiumId={cosiumId} />
        </ErrorBoundary>
      )}
      {activeTab === "fidelite" && (
        <ErrorBoundary name="TabFidelite">
          <TabFidelite clientId={clientId} />
        </ErrorBoundary>
      )}
      {activeTab === "sav" && (
        <ErrorBoundary name="TabSAV">
          <TabSAV cosiumId={cosiumId} />
        </ErrorBoundary>
      )}
      {activeTab === "rapprochement" && (
        <ErrorBoundary name="TabRapprochement">
          <TabRapprochement clientId={clientId} />
        </ErrorBoundary>
      )}
      {activeTab === "pec" && (
        <ErrorBoundary name="TabPEC">
          <TabPEC clientId={clientId} />
        </ErrorBoundary>
      )}
      {activeTab === "activite" && (
        <ErrorBoundary name="TabActivite">
          <TabActivite
            clientId={clientId}
            interactions={interactions}
            devis={devis}
            factures={factures}
            paiements={paiements}
          />
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
