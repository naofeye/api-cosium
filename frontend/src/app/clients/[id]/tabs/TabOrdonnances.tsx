"use client";

import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import type { CosiumPrescription } from "@/lib/types";

interface TabOrdonnancesProps {
  cosiumId: string | number | null;
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

export function TabOrdonnances({ cosiumId }: TabOrdonnancesProps) {
  const { data, error, isLoading, mutate } = useSWR<{ items: CosiumPrescription[] }>(
    cosiumId ? `/cosium/prescriptions?customer_id=${cosiumId}&page_size=50` : null,
  );

  if (!cosiumId) {
    return (
      <EmptyState
        title="Client non lie a Cosium"
        description="Ce client n'a pas d'identifiant Cosium. Les ordonnances ne peuvent pas etre recuperees."
      />
    );
  }

  if (isLoading) return <LoadingState text="Chargement des ordonnances..." />;
  if (error) return <ErrorState message={error.message ?? "Erreur de chargement"} onRetry={() => mutate()} />;

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucune ordonnance"
        description="Aucune ordonnance trouvee pour ce client dans Cosium."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-border text-left text-text-secondary">
            <th scope="col" className="py-2 px-3 font-medium">Date</th>
            <th scope="col" className="py-2 px-3 font-medium">Prescripteur</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OD Sph</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OD Cyl</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OD Axe</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OD Add</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OG Sph</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OG Cyl</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OG Axe</th>
            <th scope="col" className="py-2 px-3 font-medium text-right">OG Add</th>
          </tr>
        </thead>
        <tbody>
          {items.map((rx) => (
            <tr key={rx.id} className="border-b border-border hover:bg-gray-50">
              <td className="py-2 px-3">
                {rx.prescription_date ? <DateDisplay date={rx.prescription_date} /> : "-"}
              </td>
              <td className="py-2 px-3">{rx.prescriber_name || "-"}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.sphere_right)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.cylinder_right)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatAxis(rx.axis_right)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.addition_right)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.sphere_left)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.cylinder_left)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatAxis(rx.axis_left)}</td>
              <td className="py-2 px-3 text-right font-mono">{formatDiopter(rx.addition_left)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
