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
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

export interface DashboardChartsProps {
  caParMois: { mois: string; ca: number }[];
  cosiumCaParMois: { mois: string; ca: number }[];
  aging: {
    buckets: { tranche: string; client: number; mutuelle: number; secu: number; total: number }[];
    total: number;
  };
  cosium: {
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
  } | null;
}

const DOC_COLORS = ["#2563eb", "#f59e0b", "#10b981"];

function formatMonth(mois: string): string {
  const [year, month] = mois.split("-");
  const months = ["Jan", "Fev", "Mar", "Avr", "Mai", "Jun", "Jul", "Aou", "Sep", "Oct", "Nov", "Dec"];
  return `${months[parseInt(month, 10) - 1]} ${year.slice(2)}`;
}

export function DashboardCharts({ caParMois, cosiumCaParMois, aging, cosium }: DashboardChartsProps) {
  // Use Cosium monthly CA if available, otherwise OptiFlow
  const hasCosCa = cosiumCaParMois.some((m) => m.ca > 0);
  const chartData = (hasCosCa ? cosiumCaParMois : caParMois).map((item) => ({
    mois: formatMonth(item.mois),
    ca: item.ca,
  }));

  // Document type distribution pie chart
  const docData =
    cosium && (cosium.invoice_count > 0 || cosium.quote_count > 0)
      ? [
          { name: "Factures", value: cosium.invoice_count },
          { name: "Devis", value: cosium.quote_count },
          { name: "Avoirs", value: cosium.credit_note_count },
        ].filter((d) => d.value > 0)
      : [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      {/* CA par mois bar chart */}
      <div
        className="rounded-xl border border-border bg-bg-card p-6 shadow-sm"
        role="figure"
        aria-label="Graphique : Evolution du chiffre d'affaires mensuel"
      >
        <h3 className="text-lg font-semibold text-text-primary mb-4">
          Evolution du CA {hasCosCa ? "(12 mois)" : "(6 mois)"}
        </h3>
        {chartData.length > 0 && chartData.some((d) => d.ca > 0) ? (
          <>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={chartData} aria-hidden="true">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="mois" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(value) => formatMoney(Number(value))} />
                <Bar dataKey="ca" name="CA" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <table className="sr-only">
              <caption>Chiffre d&apos;affaires par mois</caption>
              <thead>
                <tr>
                  <th scope="col">Mois</th>
                  <th scope="col">CA</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((item) => (
                  <tr key={item.mois}>
                    <td>{item.mois}</td>
                    <td>{formatMoney(item.ca)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="text-sm text-text-secondary py-8 text-center">Pas de donnees de facturation</p>
        )}
      </div>

      {/* Document distribution or aging */}
      {docData.length > 0 ? (
        <div
          className="rounded-xl border border-border bg-bg-card p-6 shadow-sm"
          role="figure"
          aria-label="Graphique : Repartition des documents Cosium"
        >
          <h3 className="text-lg font-semibold text-text-primary mb-4">Repartition des documents</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart aria-hidden="true">
              <Pie
                data={docData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
                dataKey="value"
                label={({ name, value }) => `${name}: ${value.toLocaleString("fr-FR")}`}
              >
                {docData.map((_, idx) => (
                  <Cell key={idx} fill={DOC_COLORS[idx % DOC_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => Number(value).toLocaleString("fr-FR")} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
          <table className="sr-only">
            <caption>Repartition des documents</caption>
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Nombre</th>
              </tr>
            </thead>
            <tbody>
              {docData.map((d) => (
                <tr key={d.name}>
                  <td>{d.name}</td>
                  <td>{d.value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          className="rounded-xl border border-border bg-bg-card p-6 shadow-sm"
          role="figure"
          aria-label="Graphique : Balance agee des creances"
        >
          <h3 className="text-lg font-semibold text-text-primary mb-4">Balance agee ({formatMoney(aging.total)})</h3>
          {aging.total > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={aging.buckets} aria-hidden="true">
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
              <table className="sr-only">
                <caption>Balance agee par tranche</caption>
                <thead>
                  <tr>
                    <th scope="col">Tranche</th>
                    <th scope="col">Client</th>
                    <th scope="col">Mutuelle</th>
                    <th scope="col">Secu</th>
                    <th scope="col">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {aging.buckets.map((b) => (
                    <tr key={b.tranche}>
                      <td>{b.tranche}</td>
                      <td>{formatMoney(b.client)}</td>
                      <td>{formatMoney(b.mutuelle)}</td>
                      <td>{formatMoney(b.secu)}</td>
                      <td>{formatMoney(b.total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <p className="text-sm text-text-secondary py-8 text-center">Aucune creance en retard</p>
          )}
        </div>
      )}
    </div>
  );
}
