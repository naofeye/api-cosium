"use client";

import { type ReactNode } from "react";
import { Header } from "./Header";

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
      <div className="px-6 py-8 max-w-[1440px] mx-auto">
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
            {description && <p className="mt-1 text-sm text-text-secondary">{description}</p>}
          </div>
          {actions && <div className="flex gap-2">{actions}</div>}
        </div>
        {children}
      </div>
    </>
  );
}
