import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/format";

interface ReminderItem {
  id: number;
  target_type: string;
  target_id: number;
  channel: string;
  status: string;
  content: string | null;
  created_at: string;
  customer_name?: string | null;
}

interface HistoriqueTabProps {
  items: ReminderItem[];
}

export function HistoriqueTab({ items }: HistoriqueTabProps) {
  if (items.length === 0) {
    return <EmptyState title="Aucune relance" description="L'historique des relances apparaitra ici." />;
  }

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-gray-50">
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">ID</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Canal</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Contenu</th>
            <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
          </tr>
        </thead>
        <tbody>
          {items.map((r) => (
            <tr key={r.id} className="border-b border-border last:border-0">
              <td className="px-4 py-3 font-mono text-text-secondary">#{r.id}</td>
              <td className="px-4 py-3 capitalize">{r.channel}</td>
              <td className="px-4 py-3">
                <StatusBadge status={r.status} />
              </td>
              <td className="px-4 py-3 max-w-xs truncate text-text-secondary">{r.content || "-"}</td>
              <td className="px-4 py-3 text-text-secondary text-xs">
                {formatDate(r.created_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
