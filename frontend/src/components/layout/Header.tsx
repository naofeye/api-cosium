"use client";

import { Bell, LogOut, User, X, Clock, Moon, Sun, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/auth";
import { logger } from "@/lib/logger";
import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { fetchJson } from "@/lib/api";
import { toggleDarkMode } from "@/lib/theme";
import { GlobalSearch } from "./GlobalSearch";
import { TenantSelector } from "./TenantSelector";
import { useSidebar } from "@/lib/sidebar-context";

interface HeaderProps {
  breadcrumb?: { label: string; href?: string }[];
}

interface TrialInfo {
  trial_days_remaining: number;
}

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

export function Header({ breadcrumb }: HeaderProps) {
  const router = useRouter();
  const [showDropdown, setShowDropdown] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { toggleMobile } = useSidebar();

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  // SWR for unread count (auto-refresh every 30s)
  const { data: unreadData } = useSWR<{ count: number }>("/notifications/unread-count", { refreshInterval: 30000 });
  const unreadCount = unreadData?.count ?? 0;

  // SWR for trial info
  const { data: trialData } = useSWR<TrialInfo>("/onboarding/status");
  const trialDays = trialData && trialData.trial_days_remaining > 0 ? trialData.trial_days_remaining : null;

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

  const toggleDropdown = () => {
    setShowDropdown(!showDropdown);
  };

  const markAllRead = () => {
    fetchJson("/notifications/read-all", { method: "PATCH" })
      .then(() => {
        mutateNotifs();
      })
      .catch((err) => {
        logger.error("[Notifications] Erreur lors du marquage comme lu:", err);
      });
  };

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  const typeColor = (type: string) => {
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
  };

  return (
    <>
      {trialDays !== null && (
        <div className="sticky top-0 z-40 flex items-center justify-center gap-2 bg-amber-400 px-4 py-1.5 text-center text-sm font-medium text-amber-900" role="alert">
          <Clock className="h-4 w-4" aria-hidden="true" />
          <span>Periode d&apos;essai — {trialDays} jours restants</span>
        </div>
      )}
      <header
        role="banner"
        className={`sticky ${trialDays !== null ? "top-[36px]" : "top-0"} z-30 flex h-16 items-center justify-between border-b border-border bg-bg-card px-3 sm:px-6 shadow-sm`}
      >
        {/* Left side: hamburger (mobile) + breadcrumb */}
        <div className="flex items-center gap-2 text-sm text-text-secondary min-w-0">
          {/* Hamburger button - visible only on mobile */}
          <button
            onClick={toggleMobile}
            className="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700 lg:hidden"
            aria-label="Ouvrir le menu"
            title="Ouvrir le menu"
          >
            <Menu className="h-5 w-5 text-text-primary" aria-hidden="true" />
          </button>

          {/* Logo on mobile (when sidebar is hidden) */}
          <span className="font-bold text-text-primary lg:hidden text-sm">OptiFlow</span>

          {/* Breadcrumb - hidden on mobile */}
          <div className="hidden sm:flex items-center gap-2">
            {breadcrumb?.map((item, i) => (
              <span key={i} className="flex items-center gap-2">
                {i > 0 && <span>/</span>}
                {item.href ? (
                  <a href={item.href} className="text-primary hover:underline">
                    {item.label}
                  </a>
                ) : (
                  <span className="text-text-primary font-medium">{item.label}</span>
                )}
              </span>
            ))}
          </div>
        </div>

        {/* Right side: search + actions */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Global search - hidden on small mobile, visible from sm */}
          <div className="hidden sm:block">
            <GlobalSearch />
          </div>
          <TenantSelector />
          <button
            onClick={() => setIsDark(toggleDarkMode())}
            className="rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label={isDark ? "Passer en mode clair" : "Passer en mode sombre"}
            title={isDark ? "Mode clair" : "Mode sombre"}
          >
            {isDark ? <Sun className="h-5 w-5 text-amber-400" aria-hidden="true" /> : <Moon className="h-5 w-5 text-gray-500" aria-hidden="true" />}
          </button>
          <div className="relative" ref={dropdownRef}>
            <button
              onClick={toggleDropdown}
              className="relative rounded-lg p-2 hover:bg-gray-100 dark:hover:bg-gray-700"
              aria-label="Notifications"
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
              <div className="absolute right-0 top-12 w-80 max-w-[calc(100vw-2rem)] rounded-xl border border-border bg-bg-card shadow-xl">
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

                <div className="max-h-80 overflow-y-auto">
                  {notifications.length === 0 ? (
                    <div className="py-8 text-center text-sm text-text-secondary">Aucune notification</div>
                  ) : (
                    notifications.map((n) => (
                      <div
                        key={n.id}
                        className={`flex gap-3 border-b border-border px-4 py-3 last:border-0 ${
                          !n.is_read ? "bg-blue-50/50 dark:bg-blue-900/20" : ""
                        }`}
                      >
                        <div className={`mt-1 h-2 w-2 shrink-0 rounded-full ${typeColor(n.type)}`} />
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-medium text-text-primary truncate">{n.title}</p>
                          <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{n.message}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>

          {/* User avatar + logout - hide logout text on mobile */}
          <div className="flex items-center gap-1 sm:gap-2">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-white"
              aria-label="Profil utilisateur"
              role="img"
            >
              <User className="h-4 w-4" aria-hidden="true" />
            </div>
            <button
              onClick={handleLogout}
              className="rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-danger"
              aria-label="Se deconnecter"
              title="Se deconnecter"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>
    </>
  );
}
