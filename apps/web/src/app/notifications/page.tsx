"use client";

import { useCallback, useMemo, useState } from "react";
import useSWR from "swr";
import { useRouter } from "next/navigation";
import { CheckCheck, Inbox, Trash2 } from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Pagination } from "@/components/ui/Pagination";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";

import { NotificationCard } from "./components/NotificationCard";
import { NotificationFilters } from "./components/NotificationFilters";
import type { FilterKey, Notification, NotificationListResponse } from "./types";
import { getEntityUrl, groupNotifications } from "./utils";

const PAGE_SIZE = 25;

export default function NotificationsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [filter, setFilter] = useState<FilterKey>("all");
  const [page, setPage] = useState(1);
  const [confirmDeleteRead, setConfirmDeleteRead] = useState(false);

  const unreadOnly = filter === "unread";
  const queryParams = `?page=${page}&page_size=${PAGE_SIZE}${unreadOnly ? "&unread_only=true" : ""}`;
  const { data, error, isLoading, mutate } = useSWR<NotificationListResponse>(`/notifications${queryParams}`);

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
      // silent : marquage opportuniste, l'utilisateur peut reessayer
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
    if (!notif.is_read) handleMarkRead(notif.id);
    const url = getEntityUrl(notif.entity_type, notif.entity_id);
    if (url) router.push(url);
  }, [handleMarkRead, router]);

  const filteredItems = useMemo(() => {
    if (!data) return [];
    if (filter === "read") return data.items.filter((n) => n.is_read);
    return data.items;
  }, [data, filter]);

  const grouped = useMemo(() => groupNotifications(filteredItems), [filteredItems]);

  if (isLoading) {
    return (
      <PageLayout title="Notifications" breadcrumb={[{ label: "Notifications" }]}>
        <LoadingState text="Chargement des notifications..." />
      </PageLayout>
    );
  }

  if (error) {
    return (
      <PageLayout title="Notifications" breadcrumb={[{ label: "Notifications" }]}>
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
          <Button variant="ghost" size="sm" onClick={() => setConfirmDeleteRead(true)}>
            <Trash2 className="h-4 w-4 mr-1" /> Supprimer les lues
          </Button>
        </div>
      }
    >
      <NotificationFilters
        current={filter}
        unreadCount={unreadCount}
        onChange={(f) => { setFilter(f); setPage(1); }}
      />

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
                {items.map((notif) => (
                  <NotificationCard
                    key={notif.id}
                    notif={notif}
                    onNavigate={handleNavigate}
                    onMarkRead={handleMarkRead}
                    onDelete={handleDelete}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {total > PAGE_SIZE && (
        <div className="mt-6">
          <Pagination total={total} page={page} pageSize={PAGE_SIZE} onChange={setPage} />
        </div>
      )}

      <ConfirmDialog
        open={confirmDeleteRead}
        title="Supprimer les notifications lues ?"
        message="Toutes les notifications deja lues seront definitivement supprimees. Cette action est irreversible."
        confirmLabel="Supprimer"
        danger
        onConfirm={() => {
          setConfirmDeleteRead(false);
          handleDeleteRead();
        }}
        onCancel={() => setConfirmDeleteRead(false)}
      />
    </PageLayout>
  );
}
