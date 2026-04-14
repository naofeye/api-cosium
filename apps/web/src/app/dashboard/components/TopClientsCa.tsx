"use client";

import Link from "next/link";
import useSWR from "swr";
import { Trophy, AlertTriangle, ArrowUpRight } from "lucide-react";
import { formatMoney } from "@/lib/format";

interface TopClient {
  customer_id: number | null;
  customer_name: string;
  customer_cosium_id: string | null;
  ca: number;
  nb_invoices: number;
  last_invoice_date: string | null;
  outstanding: number;
}

function frenchDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleDateString("fr-FR", { day: "2-digit", month: "short" });
  } catch {
    return iso.slice(0, 10);
  }
}

export function TopClientsCa() {
  const { data, error, isLoading } = useSWR<TopClient[]>(
    "/dashboard/top-clients?limit=10&months=12",
    { refreshInterval: 300000 },
  );

  if (isLoading || error || !data || data.length === 0) return null;

  const totalCa = data.reduce((sum, c) => sum + c.ca, 0);
  const totalOutstanding = data.reduce((sum, c) => sum + c.outstanding, 0);

  return (
    <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Trophy className="h-4 w-4 text-amber-600" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide">
          Top 10 clients - CA 12 derniers mois
        </h3>
        <span className="ml-auto text-xs text-text-secondary tabular-nums">
          Total : {formatMoney(totalCa)}
        </span>
      </div>
      <div className="space-y-1">
        {data.map((c, idx) => {
          const pct = totalCa > 0 ? (c.ca / data[0].ca) * 100 : 0;
          return (
            <div key={`${c.customer_id ?? "x"}-${idx}`} className="relative">
              {/* Background bar */}
              <div
                className="absolute inset-y-0 left-0 rounded-md bg-gradient-to-r from-amber-50 to-amber-100/30"
                style={{ width: `${pct}%` }}
                aria-hidden="true"
              />
              <div className="relative flex items-center gap-3 px-2 py-1.5 text-sm">
                <span className={`w-6 text-center font-bold tabular-nums ${idx < 3 ? "text-amber-700" : "text-text-secondary"}`}>
                  {idx + 1}
                </span>
                {c.customer_id ? (
                  <Link
                    href={`/clients/${c.customer_id}`}
                    className="flex-1 truncate font-medium text-text-primary hover:text-primary hover:underline flex items-center gap-1"
                  >
                    {c.customer_name}
                    <ArrowUpRight className="h-3 w-3 opacity-50" />
                  </Link>
                ) : (
                  <span className="flex-1 truncate font-medium text-text-secondary italic">
                    {c.customer_name} (non liee)
                  </span>
                )}
                <span className="text-xs text-text-secondary tabular-nums hidden sm:inline">
                  {c.nb_invoices} fact. · {frenchDate(c.last_invoice_date)}
                </span>
                {c.outstanding > 0 && (
                  <span className="inline-flex items-center gap-1 text-xs text-red-700 tabular-nums">
                    <AlertTriangle className="h-3 w-3" />
                    {formatMoney(c.outstanding)}
                  </span>
                )}
                <span className="font-bold tabular-nums text-text-primary min-w-[80px] text-right">
                  {formatMoney(c.ca)}
                </span>
              </div>
            </div>
          );
        })}
      </div>
      {totalOutstanding > 0 && (
        <p className="mt-3 text-xs text-red-700 italic">
          ⚠ {formatMoney(totalOutstanding)} d&apos;impayes parmi le top 10
        </p>
      )}
    </div>
  );
}
