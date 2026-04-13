import { Clock } from "lucide-react";
import type { CalendarEvent } from "../types";
import { formatTime } from "../utils";

export function TodayAppointments({ events }: { events: CalendarEvent[] }) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Clock className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Rendez-vous du jour
        </h3>
      </div>
      {events.length === 0 ? (
        <p className="text-sm text-text-secondary">Aucun rendez-vous aujourd&apos;hui</p>
      ) : (
        <div className="space-y-2">
          {events.map((ev) => (
            <div key={ev.id} className="flex items-center gap-3 text-sm">
              <span className="w-12 font-mono text-text-secondary">{formatTime(ev.start_date)}</span>
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: ev.category_color || "#6b7280" }}
                aria-hidden="true"
              />
              <span className="font-medium text-text-primary">{ev.customer_fullname}</span>
              <span className="text-text-secondary">{ev.category_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
