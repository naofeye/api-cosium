import type { LucideIcon, ReactNode } from "lucide-react";
import { Circle } from "lucide-react";

export interface TimelineItem {
  id: string | number;
  date: string;            // déjà formaté (ex: "12 avr. 2026, 14:30")
  title: ReactNode;
  description?: ReactNode;
  icon?: LucideIcon;
  iconColor?: string;     // ex: "bg-emerald-500"
}

export function Timeline({ items, emptyText = "Aucun événement" }: { items: TimelineItem[]; emptyText?: string }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500 italic">{emptyText}</p>;
  }

  return (
    <ol className="relative border-l-2 border-gray-200 pl-6 space-y-6">
      {items.map((it) => {
        const Icon = it.icon ?? Circle;
        const dotColor = it.iconColor ?? "bg-blue-500";
        return (
          <li key={it.id} className="relative">
            <span className={`absolute -left-[33px] top-1 flex h-5 w-5 items-center justify-center rounded-full ring-4 ring-white ${dotColor}`}>
              <Icon className="h-3 w-3 text-white" aria-hidden="true" />
            </span>
            <time className="block text-xs font-medium text-gray-500 mb-1">{it.date}</time>
            <div className="text-sm font-semibold text-gray-900">{it.title}</div>
            {it.description && (
              <div className="mt-1 text-sm text-gray-600">{it.description}</div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
