"use client";

import { Inbox, type LucideIcon } from "lucide-react";
import { type ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: LucideIcon;
  action?: ReactNode;
}

export function EmptyState({ title, description, icon: Icon = Inbox, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="rounded-full bg-gray-100 p-4">
        <Icon className="h-8 w-8 text-gray-400" aria-hidden="true" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-text-primary">{title}</h3>
      <p className="mt-2 max-w-sm text-sm text-text-secondary">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  );
}
