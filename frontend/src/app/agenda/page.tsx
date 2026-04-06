"use client";

import { useMemo } from "react";
import dynamic from "next/dynamic";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { useCosiumCalendarEvents } from "@/lib/hooks/use-api";
import { Calendar as CalendarIcon } from "lucide-react";
import Link from "next/link";
import { format, startOfMonth, endOfMonth, subDays, addDays } from "date-fns";

const AgendaCalendar = dynamic(
  () => import("./components/AgendaCalendar").then((m) => ({ default: m.AgendaCalendar })),
  {
    ssr: false,
    loading: () => <SkeletonCard />,
  },
);

export default function AgendaPage() {
  const date = useMemo(() => new Date(), []);

  // Compute date range for fetching
  const rangeStart = useMemo(() => format(subDays(startOfMonth(date), 7), "yyyy-MM-dd"), [date]);
  const rangeEnd = useMemo(() => format(addDays(endOfMonth(date), 7), "yyyy-MM-dd"), [date]);

  const { data, error, isLoading, mutate } = useCosiumCalendarEvents({
    page: 1,
    page_size: 500,
    date_from: rangeStart,
    date_to: rangeEnd,
  });

  // Loading state
  if (isLoading) {
    return (
      <PageLayout title="Agenda Cosium" breadcrumb={[{ label: "Agenda" }]}>
        <LoadingState text="Chargement de l'agenda..." />
      </PageLayout>
    );
  }

  // Error state
  if (error) {
    return (
      <PageLayout title="Agenda Cosium" breadcrumb={[{ label: "Agenda" }]}>
        <ErrorState
          message={error?.message || "Impossible de charger l'agenda."}
          onRetry={() => mutate()}
        />
      </PageLayout>
    );
  }

  // Empty state
  if (!data?.items?.length && !isLoading) {
    return (
      <PageLayout title="Agenda Cosium" breadcrumb={[{ label: "Agenda" }]}>
        <EmptyState
          title="Aucun rendez-vous"
          description="Synchronisez votre agenda Cosium depuis la page Admin."
          icon={CalendarIcon}
          action={
            <Link href="/admin">
              <Button variant="outline">Synchroniser Cosium</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  return (
    <PageLayout
      title="Agenda Cosium"
      description={`${data?.total ?? 0} rendez-vous synchronises`}
      breadcrumb={[{ label: "Agenda" }]}
    >
      <AgendaCalendar events={data?.items ?? []} total={data?.total ?? 0} />
    </PageLayout>
  );
}
