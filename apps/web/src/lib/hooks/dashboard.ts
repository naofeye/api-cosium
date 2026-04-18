import useSWR from "swr";
import type { DashboardSummary } from "@/lib/types";

// --- Dashboard ---
export function useDashboard() {
  return useSWR<DashboardSummary>("/dashboard/summary", { refreshInterval: 60000 });
}

export function useBestContactHour() {
  return useSWR(`/dashboard/best-contact-hour`);
}

export function useDashboardTrends() {
  return useSWR(`/dashboard/trends`);
}

export function useProductMix(days: number = 90) {
  return useSWR(`/dashboard/product-mix?days=${days}`);
}

// --- Analytics (generique) ---
export function useAnalytics(type: string, params?: { date_from?: string; date_to?: string }) {
  const sp = new URLSearchParams();
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  const query = sp.toString() ? `?${sp}` : "";
  return useSWR(`/analytics/${type}${query}`);
}
