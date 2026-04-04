import "./globals.css";
import type { ReactNode } from "react";
import { AuthLayout } from "@/components/layout/AuthLayout";

export const metadata = { title: "OptiFlow AI", description: "Plateforme metier pour opticiens" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>
        <AuthLayout>{children}</AuthLayout>
      </body>
    </html>
  );
}
