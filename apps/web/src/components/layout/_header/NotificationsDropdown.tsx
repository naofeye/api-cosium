"use client";

import { Bell, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { fetchJson } from "@/lib/api";
import { logger } from "@/lib/logger";

interface NotificationItem {
  id: number;
  type: string;
  title: string;
  message: string;
  entity_type: string | null;
  entity_id: number | null;
  is_read: boolean;
  created_at: string;
}

interface NotificationList {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

function getNotificationLink(notif: NotificationItem): string | null {
  if (!notif.entity_type || !notif.entity_id) return null;
  const routes: Record<string, string> = {
    case: `/cases/${notif.entity_id}`,
    customer: `/clients/${notif.entity_id}`,
    client: `/clients/${notif.entity_id}`,
    devis: `/devis/${notif.entity_id}`,
    facture: `/factures/${notif.entity_id}`,
    payment: `/paiements`,
    pec: `/pec/${notif.entity_id}`,
    sync_customers: `/admin`,
    sync_invoices: `/admin`,
  };
  return routes[notif.entity_type] || null;
}

function typeColor(type: string) {
  switch (type) {
    case "success":
      return "bg-emerald-500";
    case "warning":
      return "bg-amber-500";
    case "action":
      return "bg-red-500";
    default:
      return "bg-blue-500";
  }
}

export function NotificationsDropdown() {
  const router = useRouter();
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // SWR for unread count (auto-refresh every 30s)
  const { data: unreadData } = useSWR<{ count: number }>(
    "/notifications/unread-count",
    { refreshInterval: 30000 },
  );
  const unreadCount = unreadData?.count ?? 0;

  // SWR for notifications dropdown (only fetch when open)
  const { data: notifData, mutate: mutateNotifs } = useSWR<NotificationList>(
    showDropdown ? "/notifications?limit=5" : null,
  );
  const notifications = notifData?.items ?? [];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const markAllRead = () => {
    fetchJson("/notifications/read-all", { method: "PATCH" })
      .then(() => {
        mutateNotifs();
      })
      .catch((err) => {
        logger.error("[Notifications] Erreur lors du marquage comme lu:", err);
      });
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="relative rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
        aria-label="Notifications"
        aria-haspopup="menu"
        aria-expanded={showDropdown}
        title="Notifications"
      >
        <Bell className="h-5 w-5 text-gray-500" aria-hidden="true" />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {showDropdown && (
        <div
          role="dialog"
          aria-modal="false"
          aria-label="Panneau de notifications"
          onKeyDown={(e) => { if (e.key === "Escape") setShowDropdown(false); }}
          className="absolute right-0 top-12 w-96 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-bg-card shadow-2xl ring-1 ring-black/5"
        >
          <div className="flex items-center justify-between border-b border-border px-4 py-3">
            <h3 className="text-sm font-semibold text-text-primary">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button onClick={markAllRead} className="text-xs text-primary hover:underline">
                  Tout marquer lu
                </button>
              )}
              <button
                onClick={() => setShowDropdown(false)}
                className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-700"
                aria-label="Fermer"
                title="Fermer"
              >
                <X className="h-3.5 w-3.5 text-text-secondary" aria-hidden="true" />
              </button>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto overscroll-contain">
            {notifications.length === 0 ? (
              <div className="py-8 text-center text-sm text-text-secondary">Aucune notification</div>
            ) : (
              notifications.map((n) => {
                const link = getNotificationLink(n);
                const handleClick = () => {
                  if (!n.is_read) {
                    fetchJson(`/notifications/${n.id}/read`, { method: "PATCH" })
                      .then(() => mutateNotifs())
                      .catch((err) => {
                        logger.error("[Notifications] Erreur lors du marquage comme lu:", err);
                      });
                  }
                  if (link) {
                    setShowDropdown(false);
                    router.push(link);
                  }
                };
                return (
                  <button
                    key={n.id}
                    type="button"
                    onClick={handleClick}
                    className={`flex w-full gap-3 border-b border-border px-4 py-3 text-left last:border-0 transition-colors ${
                      link ? "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800" : ""
                    } ${!n.is_read ? "bg-blue-50/50 dark:bg-blue-900/20" : ""}`}
                  >
                    <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${typeColor(n.type)}`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text-primary truncate">{n.title}</p>
                      <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{n.message}</p>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
