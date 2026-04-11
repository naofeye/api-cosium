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
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
} from "recharts";

const PIE_COLORS = ["#2563eb", "#8b5cf6", "#f59e0b"];

interface StatistiquesChartsProps {
  caParMois: { mois: string; ca: number }[];
  cosium: {
    total_facture_cosium: number;
    total_outstanding: number;
    total_paid: number;
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
  } | null;
}

export function StatistiquesCharts({ caParMois, cosium }: StatistiquesChartsProps) {
  const pieData = cosium
    ? [
        { name: "Factures", value: cosium.invoice_count },
        { name: "Devis", value: cosium.quote_count },
        { name: "Avoirs", value: cosium.credit_note_count },
      ]
    : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* CA par mois */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4">CA par mois</h3>
        {caParMois.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={caParMois}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
              <XAxis dataKey="mois" tick={{ fontSize: 12 }} label={{ value: "Mois", position: "insideBottomRight", offset: -5, fontSize: 11, fill: "#6b7280" }} />
              <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} label={{ value: "Montant (EUR)", angle: -90, position: "insideLeft", offset: 10, fontSize: 11, fill: "#6b7280" }} />
              <Tooltip formatter={(value) => [formatMoney(Number(value)), "Chiffre d'affaires"]} />
              <Bar dataKey="ca" name="Chiffre d'affaires" fill="#2563eb" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-text-secondary py-8 text-center">Pas de donnees</p>
        )}
      </div>

      {/* Repartition factures / devis / avoirs */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Repartition documents Cosium</h3>
        {pieData.length > 0 && pieData.some((d) => d.value > 0) ? (
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={100} paddingAngle={3} dataKey="value" label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`}>
                {pieData.map((_, idx) => (
                  <Cell key={idx} fill={PIE_COLORS[idx % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => [Number(value).toLocaleString("fr-FR"), "Documents"]} />
              <Legend verticalAlign="bottom" height={36} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-text-secondary py-8 text-center">Aucune donnee Cosium</p>
        )}
      </div>
    </div>
  );
}
