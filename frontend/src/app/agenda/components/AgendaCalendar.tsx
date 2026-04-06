"use client";

import { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { X, User, Clock, MapPin, FileText } from "lucide-react";
import { Calendar, dateFnsLocalizer, type View, type EventPropGetter } from "react-big-calendar";
import { format, parse, startOfWeek, getDay } from "date-fns";
import { fr } from "date-fns/locale";
import type { CosiumCalendarEvent } from "@/lib/types";
import "react-big-calendar/lib/css/react-big-calendar.css";

/* ------------------------------------------------------------------ */
/* date-fns localizer (French)                                        */
/* ------------------------------------------------------------------ */
const locales = { "fr": fr };
const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek: () => startOfWeek(new Date(), { weekStartsOn: 1 }),
  getDay,
  locales,
});

/* ------------------------------------------------------------------ */
/* French messages for toolbar                                        */
/* ------------------------------------------------------------------ */
const frMessages = {
  allDay: "Journee",
  previous: "Precedent",
  next: "Suivant",
  today: "Aujourd'hui",
  month: "Mois",
  week: "Semaine",
  day: "Jour",
  agenda: "Liste",
  date: "Date",
  time: "Heure",
  event: "Evenement",
  noEventsInRange: "Aucun rendez-vous sur cette periode.",
  showMore: (total: number) => `+${total} de plus`,
};

/* ------------------------------------------------------------------ */
/* Calendar event type                                                */
/* ------------------------------------------------------------------ */
interface CalEvent {
  id: number;
  title: string;
  start: Date;
  end: Date;
  resource: CosiumCalendarEvent;
}

/* ------------------------------------------------------------------ */
/* Status helpers                                                     */
/* ------------------------------------------------------------------ */
function eventStatusLabel(event: CosiumCalendarEvent): { label: string; status: string } {
  if (event.canceled) return { label: "Annule", status: "refuse" };
  if (event.missed) return { label: "Absent", status: "retard" };
  if (event.status === "CONFIRMED") return { label: "Confirme", status: "acceptee" };
  return { label: event.status || "Inconnu", status: "en_attente" };
}

function formatTimeFr(d: Date): string {
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

/* ------------------------------------------------------------------ */
/* Event popup                                                        */
/* ------------------------------------------------------------------ */
function EventPopup({
  event,
  onClose,
}: {
  event: CalEvent;
  onClose: () => void;
}) {
  const router = useRouter();
  const raw = event.resource;
  const { label, status } = eventStatusLabel(raw);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-md rounded-xl border border-border bg-bg-card p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={`Details du rendez-vous : ${raw.customer_fullname || raw.subject}`}
      >
        <button
          onClick={onClose}
          className="absolute right-3 top-3 rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-700"
          aria-label="Fermer"
          title="Fermer"
        >
          <X className="h-4 w-4 text-text-secondary" aria-hidden="true" />
        </button>

        {raw.category_color && (
          <div
            className="mb-4 h-1.5 w-16 rounded-full"
            style={{ backgroundColor: raw.category_color }}
          />
        )}

        <h3 className="text-lg font-semibold text-text-primary mb-1">
          {raw.customer_fullname || raw.subject || "Rendez-vous"}
        </h3>

        <div className="flex items-center gap-2 mb-4">
          {raw.category_name && (
            <span className="inline-flex items-center gap-1 text-sm text-text-secondary">
              {raw.category_color && (
                <span
                  className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: raw.category_color }}
                  aria-hidden="true"
                />
              )}
              {raw.category_name}
            </span>
          )}
          <StatusBadge status={status} label={label} />
        </div>

        <div className="space-y-2 text-sm text-text-secondary">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span>
              {formatTimeFr(event.start)} - {formatTimeFr(event.end)}
              {" le "}
              {format(event.start, "EEEE d MMMM yyyy", { locale: fr })}
            </span>
          </div>

          {raw.site_name && (
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 shrink-0" aria-hidden="true" />
              <span>{raw.site_name}</span>
            </div>
          )}

          {raw.observation && (
            <div className="flex items-start gap-2">
              <FileText className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
              <span className="break-words">{raw.observation}</span>
            </div>
          )}
        </div>

        <div className="mt-5 flex items-center gap-2">
          {raw.customer_fullname && raw.customer_number && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                onClose();
                router.push(`/clients?search=${encodeURIComponent(raw.customer_fullname)}`);
              }}
            >
              <User className="h-4 w-4 mr-1" aria-hidden="true" />
              Voir le client
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* AgendaCalendar component                                           */
/* ------------------------------------------------------------------ */
interface AgendaCalendarProps {
  events: CosiumCalendarEvent[];
  total: number;
}

export function AgendaCalendar({ events, total }: AgendaCalendarProps) {
  const [view, setView] = useState<View>("week");
  const [date, setDate] = useState(new Date());
  const [selectedEvent, setSelectedEvent] = useState<CalEvent | null>(null);

  const calendarEvents: CalEvent[] = useMemo(() => {
    return events
      .filter((e) => e.start_date)
      .map((e) => {
        const start = new Date(e.start_date!);
        const end = e.end_date ? new Date(e.end_date) : new Date(start.getTime() + 30 * 60 * 1000);
        return {
          id: e.id,
          title: e.customer_fullname || e.category_name || "RDV",
          start,
          end,
          resource: e,
        };
      });
  }, [events]);

  const eventPropGetter: EventPropGetter<CalEvent> = useCallback((event) => {
    const raw = event.resource;
    const bgColor = raw.category_color || "#3b82f6";

    if (raw.canceled) {
      return {
        style: {
          backgroundColor: "#9ca3af",
          color: "#fff",
          borderRadius: "6px",
          border: "none",
          opacity: 0.6,
          textDecoration: "line-through",
        },
      };
    }

    if (raw.missed) {
      return {
        style: {
          backgroundColor: "#ef4444",
          color: "#fff",
          borderRadius: "6px",
          border: "none",
        },
      };
    }

    return {
      style: {
        backgroundColor: bgColor,
        color: "#fff",
        borderRadius: "6px",
        border: "none",
      },
    };
  }, []);

  const handleSelectEvent = useCallback((event: CalEvent) => {
    setSelectedEvent(event);
  }, []);

  return (
    <>
      <div className="optiflow-calendar rounded-xl border border-border bg-bg-card p-4 shadow-sm">
        <Calendar<CalEvent>
          localizer={localizer}
          events={calendarEvents}
          startAccessor="start"
          endAccessor="end"
          defaultView="week"
          view={view}
          onView={setView}
          date={date}
          onNavigate={setDate}
          views={["month", "week", "day"]}
          messages={frMessages}
          culture="fr"
          eventPropGetter={eventPropGetter}
          onSelectEvent={handleSelectEvent}
          style={{ minHeight: 650 }}
          popup
          step={15}
          timeslots={4}
          min={new Date(2000, 0, 1, 7, 0)}
          max={new Date(2000, 0, 1, 21, 0)}
        />
      </div>

      {selectedEvent && (
        <EventPopup
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}
    </>
  );
}
