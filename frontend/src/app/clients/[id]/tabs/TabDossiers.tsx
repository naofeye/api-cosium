"use client";

import { useRouter } from "next/navigation";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";

interface Dossier {
  id: number;
  statut: string;
  source: string;
  created_at: string;
}

interface TabDossiersProps {
  dossiers: Dossier[];
}

export function TabDossiers({ dossiers }: TabDossiersProps) {
  const router = useRouter();

  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      {dossiers.length === 0 ? (
        <div className="p-6">
          <EmptyState title="Aucun dossier" description="Ce client n'a pas encore de dossier." />
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="px-4 py-3 text-left font-medium text-text-secondary">ID</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Statut</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Source</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
            </tr>
          </thead>
          <tbody>
            {dossiers.map((d) => (
              <tr
                key={d.id}
                className="border-b last:border-0 cursor-pointer hover:bg-gray-50"
                onClick={() => router.push(`/cases/${d.id}`)}
              >
                <td className="px-4 py-3 font-mono">#{d.id}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={d.statut} />
                </td>
                <td className="px-4 py-3">{d.source || "—"}</td>
                <td className="px-4 py-3">
                  <DateDisplay date={d.created_at} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
