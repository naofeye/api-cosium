"use client";

import { type ReactNode } from "react";
import { Header } from "./Header";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";

interface PageLayoutProps {
  title: string;
  description?: string;
  breadcrumb?: { label: string; href?: string }[];
  actions?: ReactNode;
  children: ReactNode;
}

export function PageLayout({ title, description, breadcrumb, actions, children }: PageLayoutProps) {
  return (
    <>
      <Header breadcrumb={breadcrumb} />
      <div className="px-3 sm:px-6 py-4 sm:py-8 max-w-[1440px] mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 mb-6 sm:mb-8">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-text-primary">{title}</h1>
            {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
        <ErrorBoundary name="PageLayout-children">{children}</ErrorBoundary>
      </div>
    </>
  );
}
