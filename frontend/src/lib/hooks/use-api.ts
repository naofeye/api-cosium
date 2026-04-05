import useSWR, { type SWRConfiguration } from "swr";
import type {
  Case,
  CosiumInvoice,
  Customer,
  Devis,
  DevisDetail,
  Facture,
  FactureDetail,
  PecRequest,
  Notification,
  ActionItem,
  DashboardSummary,
  PaginatedResponse,
  BankTransaction,
} from "@/lib/types";

// --- Cases ---
export function useCases() {
  return useSWR<Case[]>("/cases");
}

export function useCase(id: number | string) {
  return useSWR<Case>(`/cases/${id}`);
}

// --- Clients ---
export function useClients(params?: { q?: string; page?: number; page_size?: number }) {
  const sp = new URLSearchParams();
  if (params?.q) sp.set("q", params.q);
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  return useSWR<PaginatedResponse<Customer>>(`/clients?${sp}`);
}

export function useClient(id: number | string) {
  return useSWR<Customer>(`/clients/${id}`);
}

// --- Devis ---
export function useDevisList() {
  return useSWR<Devis[]>("/devis");
}

export function useDevisDetail(id: number | string) {
  return useSWR<DevisDetail>(`/devis/${id}`);
}

// --- Factures ---
export function useFactures() {
  return useSWR<Facture[]>("/factures");
}

export function useFactureDetail(id: number | string) {
  return useSWR<FactureDetail>(`/factures/${id}`);
}

// --- PEC ---
export function usePecRequests() {
  return useSWR<PecRequest[]>("/pec");
}

// --- Payments ---
export function usePayments(caseId: number | string) {
  return useSWR<{ total_due: number; total_paid: number; remaining: number; items: unknown[] }>(
    `/cases/${caseId}/payments`,
  );
}

// --- Banking ---
export function useBankTransactions(params?: { unmatched?: boolean }) {
  const path = params?.unmatched ? "/banking/unmatched" : "/banking/transactions";
  return useSWR<{ items: BankTransaction[]; total: number }>(path);
}

// --- Notifications ---
export function useNotifications() {
  return useSWR<{ items: Notification[]; total: number; unread_count: number }>("/notifications");
}

export function useUnreadCount(config?: SWRConfiguration) {
  return useSWR<{ count: number }>("/notifications/unread-count", { refreshInterval: 30000, ...config });
}

// --- Action Items ---
export function useActionItems() {
  return useSWR<{ items: ActionItem[]; total: number; counts: Record<string, number> }>("/action-items");
}

// --- Dashboard ---
export function useDashboard() {
  return useSWR<DashboardSummary>("/dashboard/summary");
}

// --- Analytics ---
export function useAnalytics(type: string, params?: { date_from?: string; date_to?: string }) {
  const sp = new URLSearchParams();
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  const query = sp.toString() ? `?${sp}` : "";
  return useSWR(`/analytics/${type}${query}`);
}

// --- Cosium Invoices ---
export function useCosiumInvoices(params?: {
  page?: number;
  page_size?: number;
  type_filter?: string;
  settled?: boolean | null;
  search?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.type_filter) sp.set("type_filter", params.type_filter);
  if (params?.settled !== undefined && params?.settled !== null) sp.set("settled", String(params.settled));
  if (params?.search) sp.set("search", params.search);
  return useSWR<PaginatedResponse<CosiumInvoice>>(`/cosium-invoices?${sp}`);
}

// --- Client 360 ---
export function useClient360(id: number | string) {
  return useSWR(`/clients/${id}/360`);
}
