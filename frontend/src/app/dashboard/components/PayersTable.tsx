import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatMoney } from "@/lib/format";

interface Payer {
  name: string;
  type: string;
  acceptance_rate: number;
  total_requested: number;
  total_accepted: number;
}

interface PayersTableProps {
  payers: Payer[];
}

export function PayersTable({ payers }: PayersTableProps) {
  if (payers.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold text-text-primary mb-4">Performance organismes payeurs</h3>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border">
            <th scope="col" className="pb-2 text-left font-medium text-text-secondary">Organisme</th>
            <th scope="col" className="pb-2 text-left font-medium text-text-secondary">Type</th>
            <th scope="col" className="pb-2 text-right font-medium text-text-secondary">Demande</th>
            <th scope="col" className="pb-2 text-right font-medium text-text-secondary">Accorde</th>
            <th scope="col" className="pb-2 text-center font-medium text-text-secondary">Taux acceptation</th>
          </tr>
        </thead>
        <tbody>
          {payers.map((p, i) => (
            <tr key={i} className="border-b border-border last:border-0">
              <td className="py-2 font-medium">{p.name}</td>
              <td className="py-2">
                <StatusBadge status={p.type} />
              </td>
              <td className="py-2 text-right tabular-nums">{formatMoney(p.total_requested)}</td>
              <td className="py-2 text-right tabular-nums">{formatMoney(p.total_accepted)}</td>
              <td className="py-2 text-center">
                <span
                  className={`font-semibold ${p.acceptance_rate > 80 ? "text-emerald-700" : p.acceptance_rate > 50 ? "text-amber-700" : "text-red-700"}`}
                >
                  {p.acceptance_rate}%
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
