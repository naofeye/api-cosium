"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { LayoutDashboard, Users, Calendar, Receipt } from "lucide-react";
import { Sidebar } from "./Sidebar";
import { SSEListener } from "./SSEListener";
import { StatsFooter } from "./StatsFooter";
import { ToastProvider } from "@/components/ui/Toast";
import { SWRProvider } from "@/lib/swr";
import { initTheme } from "@/lib/theme";
import { initShortcuts } from "@/lib/shortcuts";
import { SidebarProvider } from "@/lib/sidebar-context";
import { KeyboardShortcutsHelp } from "@/components/ui/KeyboardShortcuts";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicPage = pathname === "/login" || pathname?.startsWith("/onboarding") || pathname === "/getting-started";

  useEffect(() => {
    initTheme();
    const cleanup = initShortcuts();
    return cleanup;
  }, []);

  if (isPublicPage) {
    return <ToastProvider>{children}</ToastProvider>;
  }

  return (
    <SWRProvider>
      <ToastProvider>
        <SidebarProvider>
          <SSEListener />
          <div className="flex min-h-screen">
            <Sidebar />
            <main id="main-content" className="flex-1 ml-0 lg:ml-64 min-h-screen bg-bg-page transition-[margin] duration-200 pb-20 lg:pb-8">
              {children}
            </main>
          </div>

          {/* Mobile bottom navigation */}
          <MobileBottomBar currentPath={pathname} />

          <StatsFooter />
          <KeyboardShortcutsHelp />
        </SidebarProvider>
      </ToastProvider>
    </SWRProvider>
  );
}

const MOBILE_NAV_ITEMS = [
  { href: "/dashboard", label: "Accueil", icon: LayoutDashboard },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/agenda", label: "Agenda", icon: Calendar },
  { href: "/cosium-factures", label: "Factures", icon: Receipt },
] as const;

function MobileBottomBar({ currentPath }: { currentPath: string | null }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex items-center justify-around py-2 lg:hidden z-40">
      {MOBILE_NAV_ITEMS.map(({ href, label, icon: Icon }) => {
        const isActive = currentPath === href || currentPath?.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={`flex flex-col items-center text-xs gap-0.5 px-2 py-1 rounded-lg transition-colors ${
              isActive
                ? "text-primary font-medium"
                : "text-text-secondary hover:text-text-primary"
            }`}
            aria-label={label}
          >
            <Icon className="h-5 w-5" aria-hidden="true" />
            <span>{label}</span>
          </Link>
        );
      })}
    </div>
  );
}
