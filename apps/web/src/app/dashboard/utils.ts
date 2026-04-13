export type PeriodKey = "today" | "7d" | "30d" | "90d" | "all";

export const PERIODS: { key: PeriodKey; label: string; days: number }[] = [
  { key: "today", label: "Aujourd'hui", days: 0 },
  { key: "7d", label: "7 jours", days: 7 },
  { key: "30d", label: "30 jours", days: 30 },
  { key: "90d", label: "90 jours", days: 90 },
  { key: "all", label: "Tout", days: -1 },
];

export function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function getDateRange(period: PeriodKey): { date_from: string; date_to: string } {
  const now = new Date();
  const date_to = formatDate(now);
  if (period === "all") return { date_from: "", date_to: "" };
  if (period === "today") return { date_from: date_to, date_to };
  const days = PERIODS.find((p) => p.key === period)!.days;
  const from = new Date(now);
  from.setDate(from.getDate() - days);
  return { date_from: formatDate(from), date_to };
}

export function formatTime(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "--:--";
  }
}

export function formatRelativeTime(date: Date): string {
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return "a l'instant";
  if (seconds < 60) return `il y a ${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `il y a ${minutes}min`;
  const hours = Math.floor(minutes / 60);
  return `il y a ${hours}h`;
}
