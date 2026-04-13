import { formatMoney } from "@/lib/format";

export interface AgingBucket {
  tranche: string;       // ex: "0-30j", "31-60j", ">90j"
  client: number;
  mutuelle: number;
  secu: number;
  total: number;
}

interface Props {
  buckets: AgingBucket[];
  total?: number;
}

function _bucketColor(label: string): string {
  if (label.includes(">") || label.includes("plus")) return "text-red-700 bg-red-50";
  if (label.includes("60") || label.includes("90")) return "text-amber-700 bg-amber-50";
  if (label.includes("30")) return "text-yellow-700 bg-yellow-50";
  return "text-emerald-700 bg-emerald-50";
}

export function AgingTable({ buckets, total }: Props) {
  const computedTotal = total ?? buckets.reduce((s, b) => s + b.total, 0);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 text-left">
            <th className="px-4 py-3 font-semibold text-gray-700">Tranche</th>
            <th className="px-4 py-3 font-semibold text-gray-700 text-right">Client</th>
            <th className="px-4 py-3 font-semibold text-gray-700 text-right">Mutuelle</th>
            <th className="px-4 py-3 font-semibold text-gray-700 text-right">Sécu</th>
            <th className="px-4 py-3 font-semibold text-gray-700 text-right">Total</th>
            <th className="px-4 py-3 font-semibold text-gray-700 text-right">% du total</th>
          </tr>
        </thead>
        <tbody>
          {buckets.map((b) => {
            const pct = computedTotal > 0 ? Math.round((b.total / computedTotal) * 100) : 0;
            return (
              <tr key={b.tranche} className="border-b border-gray-100 last:border-0">
                <td className="px-4 py-3">
                  <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${_bucketColor(b.tranche)}`}>
                    {b.tranche}
                  </span>
                </td>
                <td className="px-4 py-3 text-right tabular-nums">{formatMoney(b.client)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatMoney(b.mutuelle)}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatMoney(b.secu)}</td>
                <td className="px-4 py-3 text-right tabular-nums font-semibold">{formatMoney(b.total)}</td>
                <td className="px-4 py-3 text-right text-gray-500 tabular-nums">{pct}%</td>
              </tr>
            );
          })}
          <tr className="bg-gray-50 font-semibold">
            <td className="px-4 py-3">TOTAL</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(buckets.reduce((s, b) => s + b.client, 0))}</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(buckets.reduce((s, b) => s + b.mutuelle, 0))}</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(buckets.reduce((s, b) => s + b.secu, 0))}</td>
            <td className="px-4 py-3 text-right tabular-nums">{formatMoney(computedTotal)}</td>
            <td className="px-4 py-3 text-right text-gray-500 tabular-nums">100%</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
