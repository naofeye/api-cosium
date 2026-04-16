import "./globals.css";
import type { ReactNode } from "react";
import type { Metadata, Viewport } from "next";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { ProgressBarProvider } from "@/components/layout/ProgressBar";
import { ServiceWorkerRegister } from "@/components/layout/ServiceWorkerRegister";
import { WebVitals } from "@/components/layout/WebVitals";

export const metadata: Metadata = {
  title: "OptiFlow AI — Gestion Opticien",
  description: "Plateforme de gestion pour opticiens connectee a Cosium",
  applicationName: "OptiFlow AI",
  manifest: "/manifest.json",
  icons: {
    icon: "/favicon.svg",
    apple: "/icons/icon-192.png",
  },
  keywords: ["opticien", "gestion", "cosium", "optiflow", "crm"],
  authors: [{ name: "OptiFlow AI" }],
  appleWebApp: {
    capable: true,
    title: "OptiFlow",
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  viewportFit: "cover",
  themeColor: "#2563eb",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:bg-white focus:px-4 focus:py-2 focus:rounded focus:shadow-lg focus:text-blue-700 focus:ring-2 focus:ring-blue-500"
        >
          Aller au contenu principal
        </a>
        <ProgressBarProvider />
        <ServiceWorkerRegister />
        <WebVitals />
        <AuthLayout>{children}</AuthLayout>
      </body>
    </html>
  );
}
