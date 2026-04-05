"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Calendar, X, AlertTriangle, CheckCircle } from "lucide-react";

interface CalendarEvent {
  id: number;
  cosium_id: number;
  start_date: string | null;
  end_date: string | null;
  subject: string;
  category_name: string;
  category_color: string;
  status: string;
  canceled: boolean;
  missed: boolean;
  observation: string | null;
  site_name: string | null;
}

interface TabRendezVousProps {
  events: CalendarEvent[];
}

function statusIcon(ev: CalendarEvent) {
  if (ev.canceled) return <X className="h-4 w-4 text-red-500" aria-label="Annule" />;
  if (ev.missed) return <AlertTriangle className="h-4 w-4 text-amber-500" aria-label="Manque" />;
  return <CheckCircle className="h-4 w-4 text-emerald-500" aria-label="Confirme" />;
}

function statusLabel(ev: CalendarEvent): string {
  if (ev.canceled) return "Annule";
  if (ev.missed) return "Absent";
  if (ev.status) return ev.status;
  return "Confirme";
}

function statusBadgeClass(ev: CalendarEvent): string {
  if (ev.canceled) return "bg-red-50 text-red-700 border-red-200";
  if (ev.missed) return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-emerald-50 text-emerald-700 border-emerald-200";
}

export function TabRendezVous({ events }: TabRendezVousProps) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="Aucun rendez-vous"
        description="Aucun rendez-vous trouve pour ce client dans Cosium."
      />
    );
  }

  return (
    <div className="space-y-3">
      {events.map((ev) => (
        <div
          key={ev.id}
          className={`rounded-xl border bg-bg-card p-4 shadow-sm ${
            ev.canceled ? "opacity-60 border-red-200" : "border-border"
          }`}
        >
          <div className="flex items-start justify-between">
            <div className="flex items-start gap-3">
              <div
                className="mt-0.5 h-3 w-3 rounded-full shrink-0"
                style={{ backgroundColor: ev.category_color || "#6b7280" }}
                aria-hidden="true"
              />
              <div>
                <p className="text-sm font-medium">
                  {ev.subject || ev.category_name || "Rendez-vous"}
                </p>
                <div className="flex items-center gap-2 mt-1 text-xs text-text-secondary">
                  <Calendar className="h-3.5 w-3.5" aria-hidden="true" />
                  {ev.start_date ? (
                    <span>
                      <DateDisplay date={ev.start_date} />
                      {ev.end_date && (
                        <> &mdash; <DateDisplay date={ev.end_date} /></>
                      )}
                    </span>
                  ) : (
                    <span>Date inconnue</span>
                  )}
                </div>
                {ev.category_name && (
                  <p className="text-xs text-text-secondary mt-1">
                    {ev.category_name}
                    {ev.site_name ? ` — ${ev.site_name}` : ""}
                  </p>
                )}
                {ev.observation && (
                  <p className="text-xs text-text-secondary mt-1 italic">{ev.observation}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {statusIcon(ev)}
              <span
                className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${statusBadgeClass(ev)}`}
              >
                {statusLabel(ev)}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
