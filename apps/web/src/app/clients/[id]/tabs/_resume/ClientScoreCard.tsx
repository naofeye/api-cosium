import useSWR from "swr";
import { Star } from "lucide-react";
import { formatMoney } from "@/lib/format";
import type { ClientScore } from "./types";

const COLOR_MAP: Record<string, { bg: string; text: string; border: string; ring: string }> = {
  emerald: {
    bg: "bg-emerald-50",
    text: "text-emerald-900",
    border: "border-emerald-300",
    ring: "ring-emerald-500",
  },
  blue: {
    bg: "bg-blue-50",
    text: "text-blue-900",
    border: "border-blue-300",
    ring: "ring-blue-500",
  },
  gray: {
    bg: "bg-gray-50",
    text: "text-gray-900",
    border: "border-gray-300",
    ring: "ring-gray-500",
  },
  amber: {
    bg: "bg-amber-50",
    text: "text-amber-900",
    border: "border-amber-300",
    ring: "ring-amber-500",
  },
};

export function ClientScoreCard({ clientId }: { clientId: string | number }) {
  const { data } = useSWR<ClientScore>(`/clients/${clientId}/score`, {
    shouldRetryOnError: false,
  });
  if (!data || typeof data.score !== "number" || !data.breakdown) return null;

  const c = COLOR_MAP[data.color] ?? COLOR_MAP.gray;

  return (
    <div className={`rounded-xl border ${c.border} ${c.bg} p-4`}>
      <div className="flex items-center gap-4">
        <div
          className={`flex flex-col items-center justify-center w-20 h-20 rounded-full bg-white ring-4 ${c.ring}/20 ${c.text}`}
        >
          <Star className="h-4 w-4 mb-0.5" />
          <span className="text-2xl font-bold tabular-nums">{data.score}</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className={`text-sm font-bold uppercase tracking-wide ${c.text}`}>
            {data.category}
          </p>
          <p className="text-xs text-text-secondary mt-0.5">
            CA 12 mois :{" "}
            <span className="font-semibold tabular-nums">{formatMoney(data.ca_12m)}</span>
            {" · "}
            {data.nb_factures_12m} facture{data.nb_factures_12m > 1 ? "s" : ""}
            {" · "}
            {data.years_since_first_invoice} an{data.years_since_first_invoice > 1 ? "s" : ""}{" "}
            d&apos;anciennete
          </p>
          <div className="mt-2 flex flex-wrap gap-1.5 text-[10px]">
            {Object.entries(data.breakdown).map(([k, v]) => (
              <span
                key={k}
                className={`rounded px-1.5 py-0.5 ${
                  v > 0
                    ? "bg-emerald-100 text-emerald-700"
                    : v < 0
                      ? "bg-red-100 text-red-700"
                      : "bg-gray-200 text-gray-600"
                }`}
              >
                {k} {v > 0 ? "+" : ""}
                {v}
              </span>
            ))}
          </div>
        </div>
        {data.is_renewable && (
          <span className="rounded-full bg-amber-200 text-amber-900 px-3 py-1 text-xs font-semibold whitespace-nowrap">
            Renouvellement OK
          </span>
        )}
      </div>
    </div>
  );
}
