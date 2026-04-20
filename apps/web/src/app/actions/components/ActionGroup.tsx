"use client";

import { AlertCircle, ArrowRight } from "lucide-react";
import { TYPE_LABELS, TYPE_ICONS, PRIORITY_COLORS, PRIORITY_LABELS } from "./action-types";
import type { ActionItem } from "./action-types";

interface ActionGroupProps {
  type: string;
  items: ActionItem[];
  onMarkDone: (itemId: number) => void;
  onDismiss: (itemId: number) => void;
  onNavigate: (item: ActionItem) => void;
}

export function ActionGroup({ type, items, onMarkDone, onDismiss, onNavigate }: ActionGroupProps) {
  const Icon = TYPE_ICONS[type] || AlertCircle;

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm hover:shadow-md transition-shadow duration-200">
      <div className="flex items-center gap-3 border-b border-border px-5 py-3.5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
          <Icon className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        </div>
        <h3 className="text-sm font-semibold text-text-primary">{TYPE_LABELS[type] || type}</h3>
        <span className="rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:ring-blue-800">
          {items.length}
        </span>
      </div>
      <div className="divide-y divide-border">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center gap-4 px-5 py-3.5 hover:bg-gray-50/80 dark:hover:bg-gray-800/50 transition-colors duration-150"
          >
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-text-primary">{item.title}</p>
              {item.description && (
                <p className="text-xs text-text-secondary mt-0.5">{item.description}</p>
              )}
            </div>
            <span
              className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.medium}`}
            >
              {PRIORITY_LABELS[item.priority] || item.priority}
            </span>
            <div className="flex shrink-0 items-center gap-1.5">
              <button
                onClick={() => onMarkDone(item.id)}
                className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-emerald-700 hover:bg-emerald-50 transition-colors"
                title="Marquer comme traite"
              >
                Traite
              </button>
              <button
                onClick={() => onDismiss(item.id)}
                className="rounded-lg px-2.5 py-1.5 text-xs font-medium text-text-secondary hover:bg-gray-100 transition-colors"
                title="Reporter"
              >
                Reporter
              </button>
              <button
                onClick={() => onNavigate(item)}
                className="rounded-lg p-1.5 text-primary hover:bg-blue-50 transition-colors"
                aria-label="Voir le detail"
              >
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
