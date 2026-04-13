export interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
  is_read: boolean;
  created_at: string;
}

export interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

export type FilterKey = "all" | "unread" | "read";

export const ENTITY_ROUTES: Record<string, string> = {
  case: "/cases",
  customer: "/clients",
  devis: "/devis",
  facture: "/factures",
  pec_request: "/pec",
  pec_preparation: "/pec-dashboard",
  payment: "/paiements",
  campaign: "/marketing",
};

export const TYPE_ICONS: Record<string, string> = {
  info: "bg-blue-100 text-blue-600",
  success: "bg-emerald-100 text-emerald-600",
  warning: "bg-amber-100 text-amber-600",
  error: "bg-red-100 text-red-600",
  pec: "bg-purple-100 text-purple-600",
};
