"use client";

import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";

interface PrescriptionSummary {
  id: number;
  cosium_id: number;
  prescription_date: string | null;
  prescriber_name: string | null;
  sphere_right: number | null;
  cylinder_right: number | null;
  axis_right: number | null;
  addition_right: number | null;
  sphere_left: number | null;
  cylinder_left: number | null;
  axis_left: number | null;
  addition_left: number | null;
  spectacles_json: string | null;
}

interface TabOrdonnancesProps {
  prescriptions: PrescriptionSummary[];
}

function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatAxis(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value}\u00B0`;
}

export function TabOrdonnances({ prescriptions }: TabOrdonnancesProps) {
  if (prescriptions.length === 0) {
    return (
      <EmptyState
        title="Aucune ordonnance"
        description="Aucune ordonnance trouvee pour ce client."
      />
    );
  }

  return (
    <div className="space-y-4">
      {prescriptions.map((rx) => (
        <div key={rx.id} className="rounded-xl border border-border bg-bg-card p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="text-sm font-medium">
                {rx.prescription_date ? <DateDisplay date={rx.prescription_date} /> : "Date inconnue"}
              </span>
              {rx.prescriber_name && (
                <span className="text-sm text-text-secondary ml-2">
                  Dr {rx.prescriber_name}
                </span>
              )}
            </div>
            <span className="text-xs text-text-secondary font-mono">#{rx.cosium_id}</span>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-secondary text-xs border-b border-border">
                <th className="text-left font-medium py-1.5 px-2"></th>
                <th className="text-right font-medium py-1.5 px-2">Sph</th>
                <th className="text-right font-medium py-1.5 px-2">Cyl</th>
                <th className="text-right font-medium py-1.5 px-2">Axe</th>
                <th className="text-right font-medium py-1.5 px-2">Add</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              <tr className="border-b border-border/50">
                <td className="py-1.5 px-2 font-medium font-sans">OD</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.sphere_right)}</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.cylinder_right)}</td>
                <td className="text-right py-1.5 px-2">{formatAxis(rx.axis_right)}</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.addition_right)}</td>
              </tr>
              <tr>
                <td className="py-1.5 px-2 font-medium font-sans">OG</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.sphere_left)}</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.cylinder_left)}</td>
                <td className="text-right py-1.5 px-2">{formatAxis(rx.axis_left)}</td>
                <td className="text-right py-1.5 px-2">{formatDiopter(rx.addition_left)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}
