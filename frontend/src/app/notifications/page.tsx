"use client";

import { useState, useMemo, useCallback } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import {
  Bell,
  CheckCheck,
  Trash2,
  ExternalLink,
  Inbox,
} from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Pagination } from "@/components/ui/Pagination";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";

interface Notification {
  id: number;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
  is_read: boolean;
  created_at: string;
}

interface NotificationListResponse {
  items: Notification[];
  total: number;
  unread_count: number;
}

type FilterKey = "all" | "unread" | "read";

const ENTITY_ROUTES: Record<string, string> = {
  case: "/cases",
  customer: "/clients",
  devis: "/devis",
  facture: "/factures",
  pec_request: "/pec",
  pec_preparation: "/pec-dashboard",
  payment: "/paiements",
  campaign: "/marketing",
};

function getEntityUrl(entityType: string | null, entityId: number | null): string | null {
  if (!entityType || !entityId) return null;
  const base = ENTITY_ROUTES[entityType];
  if (!base) return null;
  return `${base}/${entityId}`;
}

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return "A l'instant";
  if (diffMinutes < 60) return `Il y a ${diffMinutes} min`;
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  if (diffDays === 1) return "Hier";
  if (diffDays < 7) return `Il y a ${diffDays} jours`;
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);
  const notifDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (notifDay.getTime() >= today.getTime()) return "Aujourd'hui";
  if (notifDay.getTime() >= yesterday.getTime()) return "Hier";
  if (notifDay.getTime() >= weekAgo.getTime()) return "Cette semaine";
  return "Plus ancien";
}

function groupNotifications(items: Notification[]): { group: string; items: Notification[] }[] {
  const groups: { group: string; items: Notification[] }[] = [];
  const groupOrder = ["Aujourd'hui", "Hier", "Cette semaine", "Plus ancien"];
  const map = new Map<string, Notification[]>();

  for (const item of items) {
    const g = getDateGroup(item.created_at);
    if (!map.has(g)) map.set(g, []);
    map.get(g)!.push(item);
  }

  for (const g of groupOrder) {
    const notifs = map.get(g);
    if (notifs && notifs.length > 0) {
      groups.push({ group: g, items: notifs });
    }
  }

  return groups;
}

const TYPE_ICONS: Record<string, string> = {
  info: "bg-blue-100 text-blue-600",
  success: "bg-emerald-100 text-emerald-600",
  warning: "bg-amber-100 text-amber-600",
  error: "bg-red-100 text-red-600",
  pec: "bg-purple-100 text-purple-600",
};

export default function NotificationsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const unreadOnly = filter === "unread";
  const queryParams = `?page=${page}&page_size=${pageSize}${unreadOnly ? "&unread_only=true" : ""}`;

  const { data, error, isLoading, mutate } = useSWR<NotificationListResponse>(
    `/notifications${queryParams}`,
  );

  const handleMarkAllRead = useCallback(async () => {
    try {
      await fetchJson("/notifications/read-all", { method: "PATCH" });
      toast("Toutes les notifications marquees comme lues", "success");
      mutate();
    } catch {
      toast("Erreur lors du marquage", "error");
    }
  }, [mutate, toast]);

  const handleMarkRead = useCallback(async (id: number) => {
    try {
      await fetchJson(`/notifications/${id}/read`, { method: "PATCH" });
      mutate();
    } catch {
      // silent
    }
  }, [mutate]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await fetchJson(`/notifications/${id}`, { method: "DELETE" });
      toast("Notification supprimee", "success");
      mutate();
    } catch {
      toast("Erreur lors de la suppression", "error");
    }
  }, [mutate, toast]);

  const handleDeleteRead = useCallback(async () => {
    try {
      await fetchJson("/notifications/read", { method: "DELETE" });
      toast("Notifications lues supprimees", "success");
      mutate();
    } catch {
      toast("Erreur lors de la suppression", "error");
    }
  }, [mutate, toast]);

  const handleNavigate = useCallback((notif: Notification) => {
    if (!notif.is_read) {
      handleMarkRead(notif.id);
    }
    const url = getEntityUrl(notif.entity_type, notif.entity_id);
    if (url) {
      router.push(url);
    }
  }, [handleMarkRead, router]);

  const filteredItems = useMemo(() => {
    if (!data) return [];
    if (filter === "read") return data.items.filter((n) => n.is_read);
    return data.items;
  }, [data, filter]);

  const grouped = useMemo(() => groupNotifications(filteredItems), [filteredItems]);

  if (isLoading) {
    return (
      <PageLayout
        title="Notifications"
        breadcrumb={[{ label: "Notifications" }]}
      >
        <LoadingState text="Chargement des notifications..." />
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout
        title="Notifications"
        breadcrumb={[{ label: "Notifications" }]}
      >
        <ErrorState
          message={error?.message ?? "Impossible de charger les notifications."}
          onRetry={() => mutate()}
        />
      </PageLayout>
    );
  }

  const total = data?.total ?? 0;
  const unreadCount = data?.unread_count ?? 0;

  return (
    <PageLayout
      title="Notifications"
      description={`${unreadCount} non lue${unreadCount > 1 ? "s" : ""}`}
      breadcrumb={[{ label: "Notifications" }]}
      actions={
        <div className="flex gap-2">
          {unreadCount > 0 && (
            <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
              <CheckCheck className="h-4 w-4 mr-1" /> Tout marquer comme lu
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={handleDeleteRead}>
            <Trash2 className="h-4 w-4 mr-1" /> Supprimer les lues
          </Button>
        </div>
      }
    >
      {/* Filters */}
      <div className="flex items-center gap-2 mb-6">
        {(["all", "unread", "read"] as FilterKey[]).map((f) => {
          const labels: Record<FilterKey, string> = {
            all: "Toutes",
            unread: "Non lues",
            read: "Lues",
          };
          return (
            <button
              key={f}
              onClick={() => { setFilter(f); setPage(1); }}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                filter === f
                  ? "bg-primary text-white"
                  : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
              }`}
            >
              {labels[f]}
              {f === "unread" && unreadCount > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-red-500 text-white text-xs font-medium px-1.5 min-w-[20px]">
                  {unreadCount}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Content */}
      {filteredItems.length === 0 ? (
        <EmptyState
          title={filter === "unread" ? "Aucune notification non lue" : "Aucune notification"}
          description={
            filter === "unread"
              ? "Toutes vos notifications ont ete lues."
              : "Vous n'avez pas encore recu de notifications."
          }
          icon={Inbox}
        />
      ) : (
        <div className="space-y-6">
          {grouped.map(({ group, items }) => (
            <div key={group}>
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                {group}
              </h3>
              <div className="space-y-2">
                {items.map((notif) => {
                  const typeClass = TYPE_ICONS[notif.type] ?? TYPE_ICONS.info;
                  const entityUrl = getEntityUrl(notif.entity_type, notif.entity_id);

                  return (
                    <div
                      key={notif.id}
                      className={`rounded-xl border bg-white shadow-sm p-4 flex items-start gap-4 transition-colors ${
                        !notif.is_read
                          ? "border-blue-200 bg-blue-50/30"
                          : "border-gray-200"
                      }`}
                    >
                      {/* Icon */}
                      <div className={`shrink-0 rounded-full p-2 ${typeClass}`}>
                        <Bell className="h-4 w-4" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className={`text-sm font-medium ${!notif.is_read ? "text-gray-900" : "text-gray-700"}`}>
                            {notif.title}
                          </p>
                          {!notif.is_read && (
                            <span className="h-2 w-2 rounded-full bg-blue-600 shrink-0" />
                          )}
                        </div>
                        <p className="text-sm text-gray-500 mt-0.5 line-clamp-2">{notif.message}</p>
                        <p className="text-xs text-gray-400 mt-1">{formatRelativeDate(notif.created_at)}</p>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-1 shrink-0">
                        {entityUrl && (
                          <button
                            onClick={() => handleNavigate(notif)}
                            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
                            title="Voir le detail"
                            aria-label="Voir le detail"
                          >
                            <ExternalLink className="h-4 w-4 text-gray-400" />
                          </button>
                        )}
                        {!notif.is_read && (
                          <button
                            onClick={() => handleMarkRead(notif.id)}
                            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
                            title="Marquer comme lue"
                            aria-label="Marquer comme lue"
                          >
                            <CheckCheck className="h-4 w-4 text-gray-400" />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(notif.id)}
                          className="rounded-lg p-1.5 hover:bg-red-50 transition-colors"
                          title="Supprimer"
                          aria-label="Supprimer la notification"
                        >
                          <Trash2 className="h-4 w-4 text-gray-400 hover:text-red-500" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > pageSize && (
        <div className="mt-6">
          <Pagination
            total={total}
            page={page}
            pageSize={pageSize}
            onChange={setPage}
          />
        </div>
      )}
    </PageLayout>
  );
}
