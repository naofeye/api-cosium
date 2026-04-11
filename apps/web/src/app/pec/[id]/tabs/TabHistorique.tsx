"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { ArrowRight } from "lucide-react";

export interface HistoryItem {
  id: number;
  old_status: string;
  new_status: string;
  comment: string | null;
  created_at: string;
}

export interface TabHistoriqueProps {
  history: HistoryItem[];
}

export function TabHistorique({ history }: TabHistoriqueProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      {history.length === 0 ? (
        <EmptyState title="Aucun historique" description="L'historique des changements apparaitra ici." />
      ) : (
        <div className="space-y-4">
          {history.map((h) => (
            <div key={h.id} className="flex items-start gap-3 border-b border-border pb-3 last:border-0 last:pb-0">
              <ArrowRight className="h-4 w-4 text-text-secondary mt-0.5 shrink-0" />
              <div>
                <div className="flex items-center gap-2 text-sm">
                  {h.old_status && <StatusBadge status={h.old_status} />}
                  {h.old_status && <ArrowRight className="h-3 w-3 text-text-secondary" />}
                  <StatusBadge status={h.new_status} />
                </div>
                {h.comment && <p className="text-xs text-text-secondary mt-1">{h.comment}</p>}
                <p className="text-xs text-text-secondary mt-0.5">
                  <DateDisplay date={h.created_at} />
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
