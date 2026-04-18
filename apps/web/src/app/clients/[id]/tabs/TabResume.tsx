"use client";

import { ClientScoreCard } from "./_resume/ClientScoreCard";
import { QuickNotesSection } from "./_resume/QuickNotesSection";
import { RecentInvoicesTable } from "./_resume/RecentInvoicesTable";
import { RenewalBanner } from "./_resume/RenewalBanner";
import {
  CorrectionCard,
  CosiumSummaryCard,
  MutuellesCard,
  PersonalInfoCard,
  RecentInteractionsCard,
} from "./_resume/SummaryCards";
import type {
  CalendarEvent,
  ClientMutuelleInfo,
  CorrectionActuelle,
  CosiumInvoice,
  Interaction,
} from "./_resume/types";

interface TabResumeProps {
  clientId: string | number;
  firstName: string;
  lastName: string;
  phone: string | null;
  email: string | null;
  socialSecurityNumber: string | null;
  postalCode: string | null;
  city: string | null;
  renewalEligible: boolean;
  renewalMonths: number;
  interactions: Interaction[];
  correction: CorrectionActuelle | null;
  totalCaCosium: number;
  lastVisitDate: string | null;
  nextRdv: CalendarEvent | null;
  cosiumInvoices: CosiumInvoice[];
  mutuelles: ClientMutuelleInfo[];
  onNoteAdded?: () => void;
}

export function TabResume({
  clientId,
  firstName,
  lastName,
  phone,
  email,
  socialSecurityNumber,
  postalCode,
  city,
  renewalEligible,
  renewalMonths,
  interactions,
  correction,
  totalCaCosium,
  lastVisitDate,
  nextRdv,
  cosiumInvoices,
  mutuelles,
  onNoteAdded,
}: TabResumeProps) {
  return (
    <div className="space-y-6">
      <ClientScoreCard clientId={clientId} />

      {renewalEligible && <RenewalBanner renewalMonths={renewalMonths} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PersonalInfoCard
          firstName={firstName}
          lastName={lastName}
          phone={phone}
          email={email}
          socialSecurityNumber={socialSecurityNumber}
          postalCode={postalCode}
          city={city}
        />
        <CosiumSummaryCard
          totalCaCosium={totalCaCosium}
          lastVisitDate={lastVisitDate}
          nextRdv={nextRdv}
        />
        <MutuellesCard mutuelles={mutuelles} />
        {correction && <CorrectionCard correction={correction} />}
        <RecentInteractionsCard interactions={interactions} />
      </div>

      <QuickNotesSection
        clientId={clientId}
        interactions={interactions}
        onNoteAdded={onNoteAdded}
      />

      <RecentInvoicesTable invoices={cosiumInvoices ?? []} />
    </div>
  );
}
