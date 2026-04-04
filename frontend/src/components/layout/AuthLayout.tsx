"use client";

import { usePathname } from "next/navigation";
import { Sidebar } from "./Sidebar";
import { ToastProvider } from "@/components/ui/Toast";
import { SWRProvider } from "@/lib/swr";

export function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicPage = pathname === "/login" || pathname?.startsWith("/onboarding") || pathname === "/getting-started";

  if (isPublicPage) {
    return <ToastProvider>{children}</ToastProvider>;
  }

  return (
    <SWRProvider>
      <ToastProvider>
        <div className="flex min-h-screen">
          <Sidebar />
          <main className="flex-1 ml-64 min-h-screen bg-bg-page">{children}</main>
        </div>
      </ToastProvider>
    </SWRProvider>
  );
}
