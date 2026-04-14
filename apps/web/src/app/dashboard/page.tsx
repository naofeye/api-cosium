"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";

import { PageLayout } from "@/components/layout/PageLayout";
import { ErrorState } from "@/components/ui/ErrorState";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { OnboardingGuide } from "@/components/ui/OnboardingGuide";
import { SkeletonCard } from "@/components/ui/SkeletonCard";

import { ActionItemsBreakdown } from "./components/ActionItemsBreakdown";
import { CosiumCockpitKPIs } from "./components/CosiumCockpitKPIs";
import { DashboardKPIs } from "./components/DashboardKPIs";
import { DashboardSections } from "./components/DashboardSections";
import { IntelligenceDocBanner } from "./components/IntelligenceDocBanner";
import { OverdueInvoicesPanel } from "./components/OverdueInvoicesPanel";
import { PayersTable } from "./components/PayersTable";
import { PeriodSelector } from "./components/PeriodSelector";
import { QuickActions } from "./components/QuickActions";
import { QuickLinks } from "./components/QuickLinks";
import { ReconciliationBanner } from "./components/ReconciliationBanner";
import { RecentActivity } from "./components/RecentActivity";
import { RenewalSection } from "./components/RenewalSection";
import { TodayAppointments } from "./components/TodayAppointments";
import { UpcomingAppointments } from "./components/UpcomingAppointments";
import { useDashboardSWR } from "./hooks/useDashboardSWR";
import { useExportPDF } from "./hooks/useExportPDF";
import { formatDate, getDateRange, type PeriodKey } from "./utils";

const DashboardCharts = dynamic(
  () => import("./components/DashboardCharts").then((m) => ({ default: m.DashboardCharts })),
  {
    ssr: false,
    loading: () => (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    ),
  },
);

function DashboardLoading() {
  return (
    <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <SkeletonCard /><SkeletonCard />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <SkeletonCard /><SkeletonCard /><SkeletonCard />
      </div>
    </PageLayout>
  );
}

export default function DashboardPage() {
  const [period, setPeriod] = useState<PeriodKey>("all");
  const { date_from, date_to } = useMemo(() => getDateRange(period), [period]);
  const todayStr = useMemo(() => formatDate(new Date()), []);

  const { main, renewal, dataQuality, overdue, calendar, lastUpdated } = useDashboardSWR({
    dateFrom: date_from,
    dateTo: date_to,
    todayStr,
  });
  const { exporting, exportPDF } = useExportPDF(date_from, date_to);

  if (main.isLoading) return <DashboardLoading />;
  if (main.error || !main.data) {
    return (
      <PageLayout title="Erreur">
        <ErrorState message={main.error?.message ?? "Erreur"} onRetry={() => main.mutate()} />
      </PageLayout>
    );
  }

  const data = main.data;
  const { financial, aging, payers, operational, commercial, marketing, cosium, cosium_counts, cosium_ca_par_mois, comparison } = data;

  return (
    <PageLayout title="Dashboard" description="Tableau de pilotage OptiFlow" breadcrumb={[{ label: "Dashboard" }]}>
      <OnboardingGuide />

      <ErrorBoundary name="TodayAppointments">
        <TodayAppointments events={calendar.data?.events ?? []} />
      </ErrorBoundary>

      <ErrorBoundary name="UpcomingAppointments">
        <UpcomingAppointments />
      </ErrorBoundary>

      <PeriodSelector
        period={period}
        onChangePeriod={setPeriod}
        lastUpdated={lastUpdated}
        onExportPDF={exportPDF}
        exporting={exporting}
      />

      <ErrorBoundary name="ActionItemsBreakdown">
        <ActionItemsBreakdown />
      </ErrorBoundary>

      <ErrorBoundary name="CosiumCockpit">
        <CosiumCockpitKPIs />
      </ErrorBoundary>

      <ErrorBoundary name="DashboardKPIs">
        <DashboardKPIs financial={financial} cosiumCounts={cosium_counts} cosium={cosium} comparison={comparison} />
      </ErrorBoundary>

      <ErrorBoundary name="DashboardCharts">
        <DashboardCharts
          caParMois={commercial.ca_par_mois}
          cosiumCaParMois={cosium_ca_par_mois || []}
          aging={aging}
          cosium={cosium}
        />
      </ErrorBoundary>

      <ErrorBoundary name="IntelligenceDocumentaire">
        <IntelligenceDocBanner dataQuality={dataQuality.data} />
      </ErrorBoundary>

      <ErrorBoundary name="ReconciliationBanner">
        <ReconciliationBanner />
      </ErrorBoundary>

      <QuickActions />

      <ErrorBoundary name="OverdueInvoices">
        <OverdueInvoicesPanel invoices={overdue.data?.items ?? []} />
      </ErrorBoundary>

      <QuickLinks cosium={cosium} cosiumCounts={cosium_counts} />

      <div className="mb-8">
        <ErrorBoundary name="RecentActivity">
          <RecentActivity />
        </ErrorBoundary>
      </div>

      <ErrorBoundary name="DashboardSections">
        <DashboardSections operational={operational} commercial={commercial} marketing={marketing} />
      </ErrorBoundary>

      <ErrorBoundary name="RenewalSection">
        <RenewalSection renewalData={renewal.data} />
      </ErrorBoundary>

      <ErrorBoundary name="PayersTable">
        <PayersTable payers={payers.payers} />
      </ErrorBoundary>
    </PageLayout>
  );
}
