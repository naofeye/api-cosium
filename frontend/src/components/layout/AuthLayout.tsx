"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { SSEListener } from "./SSEListener";
import { ToastProvider } from "@/components/ui/Toast";
import { SWRProvider } from "@/lib/swr";
import { initTheme } from "@/lib/theme";
import { initShortcuts } from "@/lib/shortcuts";
import { SidebarProvider } from "@/lib/sidebar-context";

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
            <main id="main-content" className="flex-1 ml-0 lg:ml-64 min-h-screen bg-bg-page transition-[margin] duration-200">
              {children}
            </main>
          </div>
          <span className="fixed bottom-2 right-2 text-xs text-gray-400">v0.1.0</span>
        </SidebarProvider>
      </ToastProvider>
    </SWRProvider>
  );
}
