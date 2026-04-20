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
    <div className="relative flex flex-col items-center justify-center py-20 text-center overflow-hidden">
      {/* Subtle background decoration */}
      <div className="absolute inset-0 bg-gradient-to-b from-gray-50/50 to-transparent dark:from-gray-800/20 rounded-2xl" aria-hidden="true" />
      <div className="absolute top-8 left-1/2 -translate-x-1/2 h-32 w-32 rounded-full bg-blue-50 dark:bg-blue-900/10 blur-2xl" aria-hidden="true" />

      <div className="relative">
        <div className="mx-auto rounded-2xl bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 p-5 ring-1 ring-blue-100 dark:ring-blue-800/30">
          <Icon className="h-10 w-10 text-blue-500 dark:text-blue-400" aria-hidden="true" />
        </div>
      </div>
      <h3 className="relative mt-5 text-lg font-semibold text-text-primary">{title}</h3>
      <p className="relative mt-2 max-w-sm text-sm text-text-secondary leading-relaxed">{description}</p>
      {action && <div className="relative mt-6">{action}</div>}
    </div>
  );
}
