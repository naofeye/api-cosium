"use client";

import { BarChart3 } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { AuditLogEntry } from "@/lib/types/admin";

interface ActivityChartData {
  date: string;
  create: number;
  update: number;
  delete: number;
}

function buildActivityChart(entries: AuditLogEntry[]): ActivityChartData[] {
  const now = new Date();
  const days: ActivityChartData[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    const label = new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "short" }).format(d);
    const dateKey = d.toISOString().slice(0, 10);
    days.push({ date: label, create: 0, update: 0, delete: 0, _key: dateKey } as ActivityChartData & {
      _key: string;
    });
  }
  for (const entry of entries) {
    const entryDate = entry.created_at.slice(0, 10);
    const day = (days as (ActivityChartData & { _key: string })[]).find((d) => d._key === entryDate);
    if (day) {
      if (entry.action === "create") day.create++;
      else if (entry.action === "update") day.update++;
      else if (entry.action === "delete") day.delete++;
    }
  }
  return days;
}

interface ActivityChartProps {
  activity: AuditLogEntry[];
}

export function ActivityChart({ activity }: ActivityChartProps) {
  if (activity.length === 0) return null;

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mt-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <BarChart3 className="h-5 w-5" /> Activite des 7 derniers jours
      </h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={buildActivityChart(activity)} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Legend />
            <Bar dataKey="create" name="Creations" fill="#10b981" radius={[4, 4, 0, 0]} />
            <Bar dataKey="update" name="Modifications" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="delete" name="Suppressions" fill="#ef4444" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
