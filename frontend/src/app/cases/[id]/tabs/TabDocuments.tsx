"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Upload, Download } from "lucide-react";
import type { CaseDocument } from "./types";

interface TabDocumentsProps {
  documents: CaseDocument[];
}

export function TabDocuments({ documents }: TabDocumentsProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card shadow-sm">
      {documents.length === 0 ? (
        <div className="p-6">
          <EmptyState
            title="Aucun document"
            description="Aucun document dans ce dossier pour le moment."
            action={
              <Button>
                <Upload className="h-4 w-4 mr-2" />
                Ajouter un document
              </Button>
            }
          />
        </div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50">
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Type</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Nom du fichier</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Action</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3">
                  <StatusBadge status={doc.type} />
                </td>
                <td className="px-4 py-3 font-medium">{doc.filename}</td>
                <td className="px-4 py-3">
                  <DateDisplay date={doc.uploaded_at} />
                </td>
                <td className="px-4 py-3 text-right">
                  <a
                    href={`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1"}/documents/${doc.id}/download`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:underline text-sm"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Telecharger
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
