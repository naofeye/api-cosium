import type { FilterKey } from "../types";

const LABELS: Record<FilterKey, string> = {
  all: "Toutes",
  unread: "Non lues",
  read: "Lues",
};

const ORDER: FilterKey[] = ["all", "unread", "read"];

interface Props {
  current: FilterKey;
  unreadCount: number;
  onChange: (filter: FilterKey) => void;
}

export function NotificationFilters({ current, unreadCount, onChange }: Props) {
  return (
    <div className="flex items-center gap-2 mb-6" role="tablist" aria-label="Filtrer les notifications">
      {ORDER.map((f) => {
        const active = current === f;
        return (
          <button
            key={f}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(f)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              active
                ? "bg-primary text-white"
                : "bg-white text-gray-600 border border-gray-200 hover:bg-gray-50"
            }`}
          >
            {LABELS[f]}
            {f === "unread" && unreadCount > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-red-500 text-white text-xs font-medium px-1.5 min-w-[20px]">
                {unreadCount}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
