import { Clock, Plus, Pencil, Trash2 } from "lucide-react";

interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

const ACTION_CONFIG: Record<string, { icon: typeof Plus; color: string; bg: string; label: string }> = {
  create: { icon: Plus, color: "text-emerald-600", bg: "bg-emerald-50", label: "Creation" },
  update: { icon: Pencil, color: "text-blue-600", bg: "bg-blue-50", label: "Modification" },
  delete: { icon: Trash2, color: "text-red-600", bg: "bg-red-50", label: "Suppression" },
};

function formatActivityTime(date: string): string {
  const d = new Date(date);
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

interface RecentActivityProps {
  activity: AuditLogEntry[] | undefined;
}

export function RecentActivity({ activity }: RecentActivityProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mt-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Clock className="h-5 w-5" /> Activite recente
      </h3>
      {activity && activity.length > 0 ? (
        <div className="space-y-1">
          {activity.map((entry) => {
            const config = ACTION_CONFIG[entry.action] || ACTION_CONFIG.update;
            const Icon = config.icon;
            return (
              <div
                key={entry.id}
                className="flex items-center gap-3 rounded-lg px-3 py-2 hover:bg-gray-50 transition-colors"
              >
                <div className={`flex-shrink-0 rounded-full p-1.5 ${config.bg}`}>
                  <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary">
                    <span className={`font-medium ${config.color}`}>{config.label}</span>{" "}
                    <span className="text-text-secondary">{entry.entity_type}</span>{" "}
                    <span className="font-mono text-xs text-text-secondary">#{entry.entity_id}</span>
                  </p>
                </div>
                <span className="flex-shrink-0 text-xs text-text-secondary">
                  {formatActivityTime(entry.created_at)}
                </span>
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-text-secondary">Aucune activite recente.</p>
      )}
    </div>
  );
}
