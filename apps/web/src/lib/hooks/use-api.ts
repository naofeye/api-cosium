import useSWR, { type SWRConfiguration } from "swr";
import type {
  Case,
  CosiumInvoice,
  CosiumCalendarEvent,
  CosiumPrescription,
  CosiumPaymentItem,
  CosiumMutuelle,
  CosiumDoctor,
  CosiumProduct,
  AllDocumentsResponse,
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
  return useSWR<DashboardSummary>("/dashboard/summary", { refreshInterval: 60000 });
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
  date_from?: string;
  date_to?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.type_filter) sp.set("type_filter", params.type_filter);
  if (params?.settled !== undefined && params?.settled !== null) sp.set("settled", String(params.settled));
  if (params?.search) sp.set("search", params.search);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  return useSWR<PaginatedResponse<CosiumInvoice>>(`/cosium-invoices?${sp}`);
}

export interface CosiumInvoiceTotals {
  total_ttc: number;
  total_impaye: number;
  count: number;
}

export function useCosiumInvoiceTotals(params?: {
  type_filter?: string;
  settled?: boolean | null;
  search?: string;
  date_from?: string;
  date_to?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.type_filter) sp.set("type_filter", params.type_filter);
  if (params?.settled !== undefined && params?.settled !== null) sp.set("settled", String(params.settled));
  if (params?.search) sp.set("search", params.search);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  return useSWR<CosiumInvoiceTotals>(`/cosium-invoices/totals?${sp}`);
}

// --- Cosium Calendar Events ---
export function useCosiumCalendarEvents(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.search) sp.set("search", params.search);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  return useSWR<PaginatedResponse<CosiumCalendarEvent>>(`/cosium/calendar-events?${sp}`);
}

// --- Cosium Prescriptions ---
export function useCosiumPrescriptions(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.search) sp.set("search", params.search);
  return useSWR<PaginatedResponse<CosiumPrescription>>(`/cosium/prescriptions?${sp}`);
}

// --- Cosium Payments ---
export function useCosiumPayments(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  date_from?: string;
  date_to?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.search) sp.set("search", params.search);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  return useSWR<PaginatedResponse<CosiumPaymentItem>>(`/cosium/payments?${sp}`);
}

// --- Cosium Mutuelles ---
export function useCosiumMutuelles(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 50));
  if (params?.search) sp.set("search", params.search);
  return useSWR<PaginatedResponse<CosiumMutuelle>>(`/cosium/mutuelles?${sp}`);
}

// --- Cosium Doctors ---
export function useCosiumDoctors(params?: {
  page?: number;
  page_size?: number;
  search?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 50));
  if (params?.search) sp.set("search", params.search);
  return useSWR<PaginatedResponse<CosiumDoctor>>(`/cosium/doctors?${sp}`);
}

// --- Cosium Products ---
export function useCosiumProducts(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  family?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.search) sp.set("search", params.search);
  if (params?.family) sp.set("family", params.family);
  return useSWR<PaginatedResponse<CosiumProduct>>(`/cosium/products?${sp}`);
}

// --- All Cosium Documents ---
export function useAllCosiumDocuments(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  doc_type?: string;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.search) sp.set("search", params.search);
  if (params?.doc_type) sp.set("doc_type", params.doc_type);
  return useSWR<AllDocumentsResponse>(`/cosium-documents/all?${sp}`);
}

// --- Client 360 ---
export function useClient360(id: number | string) {
  return useSWR(`/clients/${id}/360`);
}
