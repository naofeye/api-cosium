import { useState } from "react";
import useSWR from "swr";
import type {
  CalendarEventsResponse,
  DashboardData,
  DataQualityData,
  OverdueInvoicesResponse,
  RenewalData,
} from "../types";

interface Args {
  dateFrom: string;
  dateTo: string;
  todayStr: string;
}

export function useDashboardSWR({ dateFrom, dateTo, todayStr }: Args) {
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const queryParams = dateFrom ? `?date_from=${dateFrom}&date_to=${dateTo}` : "";
  const main = useSWR<DashboardData>(`/analytics/dashboard${queryParams}`, {
    refreshInterval: 60000,
    onSuccess: () => setLastUpdated(new Date()),
  });

  const renewal = useSWR<RenewalData>("/renewals/dashboard", {
    refreshInterval: 60000,
    onError: () => { /* silent */ },
  });

  const dataQuality = useSWR<DataQualityData>("/admin/data-quality", {
    refreshInterval: 300000,
    onError: () => { /* silent */ },
  });

  const overdue = useSWR<OverdueInvoicesResponse>("/cosium-invoices?status=impayee&page_size=5", {
    refreshInterval: 120000,
    onError: () => { /* silent */ },
  });

  const calendar = useSWR<CalendarEventsResponse>(
    `/cosium/calendar-events?date_from=${todayStr}&date_to=${todayStr}&page_size=10`,
    {
      refreshInterval: 120000,
      onError: () => { /* silent */ },
    },
  );

  return {
    main,
    renewal,
    dataQuality,
    overdue,
    calendar,
    lastUpdated,
  };
}
