import "./globals.css";
import type { ReactNode } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";
import { ProgressBarProvider } from "@/components/layout/ProgressBar";

export const metadata = { title: "OptiFlow AI", description: "Plateforme metier pour opticiens" };

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
        <AuthLayout>{children}</AuthLayout>
      </body>
    </html>
  );
}
