"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";

interface Document {
  id: number;
  type: string;
  filename: string;
  uploaded_at: string;
}

interface TabDocumentsProps {
  documents: Document[];
}

export function TabDocuments({ documents }: TabDocumentsProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      {documents.length === 0 ? (
        <div className="p-6">
          <EmptyState title="Aucun document" description="Les documents apparaitront ici." />
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-gray-50">
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Type</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Fichier</th>
              <th className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id} className="border-b last:border-0">
                <td className="px-4 py-3">
                  <StatusBadge status={d.type} />
                </td>
                <td className="px-4 py-3 font-medium">{d.filename}</td>
                <td className="px-4 py-3">
                  <DateDisplay date={d.uploaded_at} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
