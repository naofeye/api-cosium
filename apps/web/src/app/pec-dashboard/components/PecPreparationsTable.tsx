import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { CompletionGauge } from "@/components/pec/CompletionGauge";
import { formatPecDate, STATUS_COLORS, STATUS_LABELS, type PecPreparationItem } from "../types";

interface Props {
  items: PecPreparationItem[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}

function CountBadge({ value, variant }: { value: number; variant: "danger" | "warning" }) {
  if (value === 0) return <span className="text-text-secondary">0</span>;
  const cls = variant === "danger"
    ? "bg-red-100 text-red-700"
    : "bg-amber-100 text-amber-700";
  return (
    <span className={`inline-flex items-center justify-center rounded-full ${cls} px-2 py-0.5 text-xs font-semibold tabular-nums`}>
      {value}
    </span>
  );
}

export function PecPreparationsTable({ items, total, page, pageSize, onPageChange }: Props) {
  const router = useRouter();
  const totalPages = Math.ceil(total / pageSize);

  const goTo = (item: PecPreparationItem) =>
    router.push(`/clients/${item.customer_id}/pec-preparation/${item.id}`);

  return (
    <>
      <div className="overflow-x-auto rounded-xl border border-border bg-bg-card shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50 text-left">
              <th className="px-4 py-3 font-semibold text-text-secondary">Client</th>
              <th className="px-4 py-3 font-semibold text-text-secondary">Statut</th>
              <th className="px-4 py-3 font-semibold text-text-secondary">Score</th>
              <th className="px-4 py-3 font-semibold text-text-secondary text-center">Erreurs</th>
              <th className="px-4 py-3 font-semibold text-text-secondary text-center">Alertes</th>
              <th className="px-4 py-3 font-semibold text-text-secondary">Date</th>
              <th className="px-4 py-3 font-semibold text-text-secondary">Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-border last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                onClick={() => goTo(item)}
              >
                <td className="px-4 py-3 font-medium text-text-primary">{item.customer_name}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[item.status] ?? "bg-gray-100 text-gray-800"}`}>
                    {STATUS_LABELS[item.status] ?? item.status}
                  </span>
                </td>
                <td className="px-4 py-3 w-48"><CompletionGauge score={item.completude_score} /></td>
                <td className="px-4 py-3 text-center"><CountBadge value={item.errors_count} variant="danger" /></td>
                <td className="px-4 py-3 text-center"><CountBadge value={item.warnings_count} variant="warning" /></td>
                <td className="px-4 py-3 text-text-secondary">{formatPecDate(item.created_at)}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={(e) => { e.stopPropagation(); goTo(item); }}
                    className="text-primary hover:underline text-sm font-medium"
                    aria-label={`Voir la preparation PEC de ${item.customer_name}`}
                  >
                    Voir
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-sm text-text-secondary">
            {total} preparation{total > 1 ? "s" : ""} au total
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Page precedente"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              Precedent
            </button>
            <span className="text-sm text-text-secondary tabular-nums">
              Page {page} / {totalPages}
            </span>
            <button
              onClick={() => onPageChange(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="inline-flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Page suivante"
            >
              Suivant
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      )}
    </>
  );
}
