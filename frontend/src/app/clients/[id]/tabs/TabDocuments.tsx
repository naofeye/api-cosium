"use client";

import { useState } from "react";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Eye, Download, X } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface Document {
  id: number;
  type: string;
  filename: string;
  uploaded_at: string;
}

interface TabDocumentsProps {
  documents: Document[];
}

function getFileExtension(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

function isPreviewableImage(filename: string): boolean {
  const ext = getFileExtension(filename);
  return ["jpg", "jpeg", "png", "bmp", "gif", "webp"].includes(ext);
}

function isPdf(filename: string): boolean {
  return getFileExtension(filename) === "pdf";
}

export function TabDocuments({ documents }: TabDocumentsProps) {
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);

  const handlePreview = (doc: Document) => {
    if (isPdf(doc.filename)) {
      window.open(`${API_BASE}/documents/${doc.id}/download?inline=true`, "_blank");
    } else if (isPreviewableImage(doc.filename)) {
      setPreviewDoc(doc);
    }
  };

  const handleDownload = (doc: Document) => {
    window.open(`${API_BASE}/documents/${doc.id}/download`, "_blank");
  };

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
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Type</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Fichier</th>
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Date</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">Actions</th>
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
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    {(isPreviewableImage(d.filename) || isPdf(d.filename)) && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handlePreview(d)}
                        aria-label={`Voir ${d.filename}`}
                      >
                        <Eye className="h-4 w-4" />
                        <span className="ml-1">Voir</span>
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(d)}
                      aria-label={`Telecharger ${d.filename}`}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Image preview modal */}
      {previewDoc && isPreviewableImage(previewDoc.filename) && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setPreviewDoc(null)}
          role="presentation"
        >
          <div
            className="relative max-w-3xl max-h-[80vh] bg-white rounded-xl shadow-xl p-2"
            role="dialog"
            aria-modal="true"
            aria-label={`Previsualisation de ${previewDoc.filename}`}
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => setPreviewDoc(null)}
              className="absolute -top-3 -right-3 rounded-full bg-white shadow-md p-1 hover:bg-gray-100"
              aria-label="Fermer la previsualisation"
            >
              <X className="h-5 w-5" />
            </button>
            <img
              src={`${API_BASE}/documents/${previewDoc.id}/download?inline=true`}
              alt={previewDoc.filename}
              className="max-h-[75vh] rounded-lg object-contain"
            />
            <p className="text-center text-sm text-text-secondary mt-2">{previewDoc.filename}</p>
          </div>
        </div>
      )}
    </div>
  );
}
