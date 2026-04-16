"use client";

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import { cn } from "@/lib/utils";

interface CalendarEvent {
  id: number | string;
  start_date: string;
  end_date?: string | null;
  subject?: string;
  canceled?: boolean;
}

interface CalendarViewProps {
  events: CalendarEvent[];
  onEventClick?: (event: CalendarEvent) => void;
  className?: string;
}

const WEEKDAYS = ["L", "M", "M", "J", "V", "S", "D"];
const MONTHS = [
  "janvier", "fevrier", "mars", "avril", "mai", "juin",
  "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
];

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function daysInMonth(d: Date): number {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();
}

function buildGrid(cursor: Date): { day: number | null; date: Date | null }[] {
  const first = startOfMonth(cursor);
  const offset = (first.getDay() + 6) % 7; // ISO: Lundi = 0
  const days = daysInMonth(cursor);
  const cells: { day: number | null; date: Date | null }[] = [];
  for (let i = 0; i < offset; i++) cells.push({ day: null, date: null });
  for (let d = 1; d <= days; d++) {
    cells.push({ day: d, date: new Date(cursor.getFullYear(), cursor.getMonth(), d) });
  }
  // Completer jusqu'a multiple de 7
  while (cells.length % 7 !== 0) cells.push({ day: null, date: null });
  return cells;
}

/**
 * Vue calendrier mensuelle avec navigation. Affiche les evenements par jour.
 */
export function CalendarView({ events, onEventClick, className }: CalendarViewProps) {
  const [cursor, setCursor] = useState(() => new Date());

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const ev of events) {
      if (!ev.start_date) continue;
      const d = new Date(ev.start_date);
      if (Number.isNaN(d.getTime())) continue;
      const key = `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`;
      const list = map.get(key) ?? [];
      list.push(ev);
      map.set(key, list);
    }
    return map;
  }, [events]);

  const cells = useMemo(() => buildGrid(cursor), [cursor]);
  const today = new Date();
  const isToday = (date: Date) =>
    date.getFullYear() === today.getFullYear() &&
    date.getMonth() === today.getMonth() &&
    date.getDate() === today.getDate();

  return (
    <div className={cn("rounded-xl border border-border bg-bg-card", className)}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <button
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}
          aria-label="Mois precedent"
          className="rounded-lg p-2 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-gray-100"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>
        <div className="flex items-center gap-2">
          <Calendar className="h-4 w-4 text-primary" aria-hidden="true" />
          <h3 className="text-base font-semibold capitalize">
            {MONTHS[cursor.getMonth()]} {cursor.getFullYear()}
          </h3>
        </div>
        <button
          onClick={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}
          aria-label="Mois suivant"
          className="rounded-lg p-2 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-gray-100"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <div className="grid grid-cols-7 border-b border-border">
        {WEEKDAYS.map((d, i) => (
          <div key={`${d}-${i}`} className="text-center text-xs font-semibold text-text-secondary py-2">
            {d}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-7">
        {cells.map((cell, i) => {
          if (!cell.date) {
            return <div key={`empty-${i}`} className="min-h-[80px] border-r border-b border-border/60 bg-gray-50/50" />;
          }
          const key = `${cell.date.getFullYear()}-${cell.date.getMonth()}-${cell.date.getDate()}`;
          const dayEvents = eventsByDay.get(key) ?? [];
          const today = isToday(cell.date);
          return (
            <div
              key={key}
              className={cn(
                "min-h-[80px] border-r border-b border-border/60 p-1.5 text-xs space-y-0.5 relative",
                today && "bg-blue-50",
              )}
            >
              <div
                className={cn(
                  "flex items-center justify-center h-6 w-6 rounded-full text-xs font-medium",
                  today ? "bg-primary text-white" : "text-text-primary",
                )}
              >
                {cell.day}
              </div>
              {dayEvents.slice(0, 3).map((ev) => (
                <button
                  key={ev.id}
                  onClick={() => onEventClick?.(ev)}
                  className={cn(
                    "block w-full text-left rounded px-1 py-0.5 truncate text-[10px]",
                    ev.canceled
                      ? "bg-gray-100 text-gray-400 line-through"
                      : "bg-blue-100 text-blue-800 hover:bg-blue-200",
                  )}
                  title={ev.subject}
                >
                  {ev.subject ?? "RDV"}
                </button>
              ))}
              {dayEvents.length > 3 && (
                <p className="text-[10px] text-text-secondary italic">
                  +{dayEvents.length - 3} de plus
                </p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
