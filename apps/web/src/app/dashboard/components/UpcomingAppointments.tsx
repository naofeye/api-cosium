"use client";

import useSWR from "swr";
import { CalendarClock } from "lucide-react";
import { SkeletonCard } from "@/components/ui/SkeletonCard";

interface UpcomingEvent {
  id: number;
  cosium_id: number;
  start_date: string | null;
  end_date: string | null;
  subject: string;
  customer_fullname: string;
  customer_number: string;
  category_name: string;
  category_color: string;
  status: string;
  site_name: string | null;
}

function formatDateTime(iso: string | null): { date: string; time: string } {
  if (!iso) return { date: "-", time: "-" };
  try {
    const d = new Date(iso);
    return {
      date: d.toLocaleDateString("fr-FR", { weekday: "short", day: "2-digit", month: "short" }),
      time: d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }),
    };
  } catch {
    return { date: iso.slice(0, 10), time: "" };
  }
}

export function UpcomingAppointments() {
  const { data, error, isLoading } = useSWR<UpcomingEvent[]>(
    "/cosium/calendar-events/upcoming?limit=8",
    { refreshInterval: 120000 },
  );

  if (isLoading) return <div className="mb-6"><SkeletonCard /></div>;
  if (error || !data || data.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <CalendarClock className="h-4 w-4 text-primary" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Prochains rendez-vous
        </h3>
        <span className="ml-auto rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs font-medium tabular-nums">
          {data.length}
        </span>
      </div>
      <div className="space-y-1.5">
        {data.map((ev) => {
          const { date, time } = formatDateTime(ev.start_date);
          return (
            <div
              key={ev.id}
              className="flex items-center gap-3 text-sm hover:bg-gray-50 rounded-lg px-2 py-1.5 transition-colors"
            >
              <div className="w-20 shrink-0">
                <p className="text-xs font-medium text-text-primary">{date}</p>
                <p className="font-mono text-xs text-text-secondary tabular-nums">{time}</p>
              </div>
              <span
                className="h-2 w-2 rounded-full shrink-0"
                style={{ backgroundColor: ev.category_color || "#6b7280" }}
                aria-hidden="true"
                title={ev.category_name}
              />
              <span className="flex-1 min-w-0 truncate font-medium text-text-primary">
                {ev.customer_fullname || ev.subject}
              </span>
              <span className="hidden sm:inline text-xs text-text-secondary truncate max-w-[120px]">
                {ev.category_name}
              </span>
              {ev.site_name && (
                <span className="hidden md:inline rounded bg-gray-100 text-gray-700 px-1.5 py-0.5 text-[10px] font-medium">
                  {ev.site_name}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
