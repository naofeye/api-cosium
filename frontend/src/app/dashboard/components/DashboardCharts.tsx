"use client";

import { formatMoney } from "@/lib/format";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";

export interface DashboardChartsProps {
  caParMois: { mois: string; ca: number }[];
  aging: {
    buckets: { tranche: string; client: number; mutuelle: number; secu: number; total: number }[];
    total: number;
  };
}

export function DashboardCharts({ caParMois, aging }: DashboardChartsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* Courbe CA par mois */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Evolution du CA (6 mois)</h3>
        {caParMois.length > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={caParMois}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="mois" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => formatMoney(Number(value))} />
              <Line type="monotone" dataKey="ca" stroke="#2563eb" strokeWidth={2} dot={{ fill: "#2563eb" }} name="CA" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-text-secondary py-8 text-center">Pas de donnees</p>
        )}
      </div>

      {/* Balance agee */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Balance agee ({formatMoney(aging.total)})</h3>
        {aging.total > 0 ? (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={aging.buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="tranche" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(value) => formatMoney(Number(value))} />
              <Legend />
              <Bar dataKey="client" name="Client" fill="#3b82f6" stackId="a" />
              <Bar dataKey="mutuelle" name="Mutuelle" fill="#8b5cf6" stackId="a" />
              <Bar dataKey="secu" name="Secu" fill="#06b6d4" stackId="a" />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-text-secondary py-8 text-center">Aucune creance en retard</p>
        )}
      </div>
    </div>
  );
}
