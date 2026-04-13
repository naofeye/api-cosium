import { ENTITY_ROUTES, type Notification } from "./types";

export function getEntityUrl(entityType: string | null, entityId: number | null): string | null {
  if (!entityType || !entityId) return null;
  const base = ENTITY_ROUTES[entityType];
  if (!base) return null;
  return `${base}/${entityId}`;
}

export function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMinutes < 1) return "A l'instant";
  if (diffMinutes < 60) return `Il y a ${diffMinutes} min`;
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  if (diffDays === 1) return "Hier";
  if (diffDays < 7) return `Il y a ${diffDays} jours`;
  return date.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
}

function getDateGroup(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);
  const notifDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  if (notifDay.getTime() >= today.getTime()) return "Aujourd'hui";
  if (notifDay.getTime() >= yesterday.getTime()) return "Hier";
  if (notifDay.getTime() >= weekAgo.getTime()) return "Cette semaine";
  return "Plus ancien";
}

const GROUP_ORDER = ["Aujourd'hui", "Hier", "Cette semaine", "Plus ancien"];

export function groupNotifications(items: Notification[]): { group: string; items: Notification[] }[] {
  const map = new Map<string, Notification[]>();
  for (const item of items) {
    const g = getDateGroup(item.created_at);
    if (!map.has(g)) map.set(g, []);
    map.get(g)!.push(item);
  }
  return GROUP_ORDER
    .map((g) => ({ group: g, items: map.get(g) ?? [] }))
    .filter((entry) => entry.items.length > 0);
}
