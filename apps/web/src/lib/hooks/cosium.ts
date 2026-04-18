import useSWR from "swr";
import type {
  AllDocumentsResponse,
  CosiumCalendarEvent,
  CosiumDoctor,
  CosiumInvoice,
  CosiumMutuelle,
  CosiumPaymentItem,
  CosiumPrescription,
  CosiumProduct,
  PaginatedResponse,
} from "@/lib/types";

// --- Cosium Invoices ---
export function useCosiumInvoices(params?: {
  page?: number;
  page_size?: number;
  type_filter?: string;
  settled?: boolean | null;
  search?: string;
  date_from?: string;
  date_to?: string;
  archived?: boolean | null;
  has_outstanding?: boolean | null;
  min_amount?: number;
  max_amount?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.page) sp.set("page", String(params.page));
  sp.set("page_size", String(params?.page_size ?? 25));
  if (params?.type_filter) sp.set("type_filter", params.type_filter);
  if (params?.settled !== undefined && params?.settled !== null)
    sp.set("settled", String(params.settled));
  if (params?.search) sp.set("search", params.search);
  if (params?.date_from) sp.set("date_from", params.date_from);
  if (params?.date_to) sp.set("date_to", params.date_to);
  if (params?.archived !== undefined && params?.archived !== null)
    sp.set("archived", String(params.archived));
  if (params?.has_outstanding !== undefined && params?.has_outstanding !== null)
    sp.set("has_outstanding", String(params.has_outstanding));
  if (params?.min_amount !== undefined) sp.set("min_amount", String(params.min_amount));
  if (params?.max_amount !== undefined) sp.set("max_amount", String(params.max_amount));
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
  if (params?.settled !== undefined && params?.settled !== null)
    sp.set("settled", String(params.settled));
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

// --- All Cosium Documents (locally downloaded) ---
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

// --- Cosium Fidelity ---
export function useCosiumFidelityCards(params?: {
  customerCosiumId?: string;
  page?: number;
  pageSize?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.customerCosiumId) sp.set("customerCosiumId", params.customerCosiumId);
  if (params?.page != null) sp.set("page", String(params.page));
  if (params?.pageSize != null) sp.set("page_size", String(params.pageSize));
  const qs = sp.toString();
  return useSWR(`/cosium/fidelity-cards${qs ? `?${qs}` : ""}`);
}

export function useCosiumSponsorships(params?: {
  customerCosiumId?: string;
  page?: number;
  pageSize?: number;
}) {
  const sp = new URLSearchParams();
  if (params?.customerCosiumId) sp.set("customerCosiumId", params.customerCosiumId);
  if (params?.page != null) sp.set("page", String(params.page));
  if (params?.pageSize != null) sp.set("page_size", String(params.pageSize));
  const qs = sp.toString();
  return useSWR(`/cosium/sponsorships${qs ? `?${qs}` : ""}`);
}
