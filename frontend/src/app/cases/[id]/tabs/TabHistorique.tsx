"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Activity, FileText, Euro, ShieldCheck, Upload, MessageSquare } from "lucide-react";
import type { CaseActivity } from "./types";

interface TabHistoriqueProps {
  activities: CaseActivity[];
}

const ACTIVITY_ICONS: Record<string, typeof Activity> = {
  devis_created: FileText,
  document_added: Upload,
  payment_received: Euro,
  pec_submitted: ShieldCheck,
  comment_added: MessageSquare,
};

const ACTIVITY_COLORS: Record<string, string> = {
  devis_created: "bg-blue-100 text-blue-600",
  document_added: "bg-emerald-100 text-emerald-600",
  payment_received: "bg-emerald-100 text-emerald-600",
  pec_submitted: "bg-sky-100 text-sky-600",
  comment_added: "bg-gray-100 text-gray-600",
};

export function TabHistorique({ activities }: TabHistoriqueProps) {
  if (activities.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <EmptyState
          title="Aucune activite"
          description="L'historique des activites de ce dossier apparaitra ici."
        />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
        <div className="space-y-6">
          {activities.map((activity) => {
            const Icon = ACTIVITY_ICONS[activity.type] || Activity;
            const colorClass = ACTIVITY_COLORS[activity.type] || "bg-gray-100 text-gray-600";
            return (
              <div key={activity.id} className="relative flex items-start gap-4 pl-10">
                <div className={`absolute left-1.5 w-5 h-5 rounded-full flex items-center justify-center ${colorClass}`}>
                  <Icon className="h-3 w-3" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary">{activity.description}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <DateDisplay date={activity.created_at} />
                    {activity.user_name && (
                      <span className="text-xs text-text-secondary">par {activity.user_name}</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
