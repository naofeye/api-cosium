"use client";

import { LogOut, User, Clock, Moon, Sun, Menu } from "lucide-react";
import { useRouter } from "next/navigation";
import { logout } from "@/lib/auth";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { toggleDarkMode } from "@/lib/theme";
import { GlobalSearch } from "./GlobalSearch";
import { TenantSelector } from "./TenantSelector";
import { useSidebar } from "@/lib/sidebar-context";
import { NotificationsDropdown } from "./_header/NotificationsDropdown";

interface HeaderProps {
  breadcrumb?: { label: string; href?: string }[];
}

interface TrialInfo {
  trial_days_remaining: number;
}

export function Header({ breadcrumb }: HeaderProps) {
  const router = useRouter();
  const [isDark, setIsDark] = useState(false);
  const { toggleMobile } = useSidebar();

  useEffect(() => {
    setIsDark(document.documentElement.classList.contains("dark"));
  }, []);

  // Ctrl+K / Cmd+K to focus the global search input
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        const searchInput = document.querySelector<HTMLInputElement>('[role="combobox"]');
        if (searchInput) {
          searchInput.focus();
        }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // SWR for trial info
  const { data: trialData } = useSWR<TrialInfo>("/onboarding/status");
  const trialDays = trialData && trialData.trial_days_remaining > 0 ? trialData.trial_days_remaining : null;

  const handleLogout = () => {
    logout();
    router.push("/login");
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
        className={`sticky ${trialDays !== null ? "top-[36px]" : "top-0"} z-30 flex h-16 items-center justify-between border-b border-border bg-bg-card px-3 sm:px-6 shadow-[0_1px_3px_rgba(0,0,0,0.05)]`}
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
          <NotificationsDropdown />

          {/* User avatar + logout - hide logout text on mobile */}
          <div className="flex items-center gap-1 sm:gap-2">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 text-white ring-2 ring-blue-100 dark:ring-blue-900/50"
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
