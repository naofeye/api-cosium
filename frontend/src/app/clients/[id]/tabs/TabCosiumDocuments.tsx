"use client";

import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Download, FileText, HardDrive, Cloud } from "lucide-react";
import type { LocalCosiumDocument, CosiumDocument } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface TabCosiumDocumentsProps {
  cosiumId: string | number | null;
}

interface LocalDocList {
  items: LocalCosiumDocument[];
  total: number;
}

interface CosiumDocList {
  items: Array<{
    document_id: number;
    label: string;
    type: string;
    date: string | null;
    size: number | null;
  }>;
  total: number;
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 o";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function TabCosiumDocuments({ cosiumId }: TabCosiumDocumentsProps) {
  // Try local docs first
  const {
    data: localData,
    error: localError,
    isLoading: localLoading,
    mutate: mutateLocal,
  } = useSWR<LocalDocList>(
    cosiumId ? `/cosium-documents/${cosiumId}/local` : null,
  );

  // Fallback to Cosium proxy if no local docs
  const hasLocalDocs = localData && localData.items && localData.items.length > 0;
  const {
    data: cosiumData,
    error: cosiumError,
    isLoading: cosiumLoading,
    mutate: mutateCosium,
  } = useSWR<CosiumDocList>(
    cosiumId && !hasLocalDocs && !localLoading ? `/cosium-documents/${cosiumId}` : null,
  );

  if (!cosiumId) {
    return (
      <EmptyState
        title="Client non lie a Cosium"
        description="Ce client n'a pas d'identifiant Cosium. Les documents ne peuvent pas etre recuperes."
      />
    );
  }

  const isLoading = localLoading || cosiumLoading;
  const error = localError || cosiumError;

  if (isLoading) return <LoadingState text="Chargement des documents..." />;
  if (error) {
    return (
      <ErrorState
        message={error.message ?? "Erreur de chargement"}
        onRetry={() => { mutateLocal(); mutateCosium(); }}
      />
    );
  }

  // Render local documents (from MinIO)
  if (hasLocalDocs) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <HardDrive className="h-4 w-4 text-emerald-600" aria-label="Stockage local" />
          <span className="text-xs text-text-secondary">
            {localData.total} document(s) stocke(s) localement
          </span>
        </div>
        {localData.items.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between rounded-lg border border-border bg-bg-card p-4"
          >
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-text-secondary" aria-hidden="true" />
              <div>
                <span className="text-sm font-medium text-text-primary">
                  {doc.name || `Document ${doc.cosium_document_id}`}
                </span>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-medium">Local</span>
                  <span className="text-xs text-text-secondary">{formatBytes(doc.size_bytes)}</span>
                  <span className="text-xs text-text-secondary">{doc.content_type}</span>
                </div>
              </div>
            </div>
            <a
              href={`${API_BASE}/cosium-documents/local/${doc.id}/download`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-1" /> Telecharger
              </Button>
            </a>
          </div>
        ))}
      </div>
    );
  }

  // Render Cosium proxy documents (fallback)
  if (cosiumData && cosiumData.items && cosiumData.items.length > 0) {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <Cloud className="h-4 w-4 text-blue-500" aria-label="Cosium cloud" />
          <span className="text-xs text-text-secondary">
            {cosiumData.total} document(s) depuis Cosium (non telecharges localement)
          </span>
        </div>
        {cosiumData.items.map((doc) => (
          <div
            key={doc.document_id}
            className="flex items-center justify-between rounded-lg border border-border bg-bg-card p-4"
          >
            <div className="flex items-center gap-3">
              <FileText className="h-5 w-5 text-text-secondary" aria-hidden="true" />
              <div>
                <span className="text-sm font-medium text-text-primary">
                  {doc.label || `Document ${doc.document_id}`}
                </span>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-medium">Cosium</span>
                  {doc.type && <span className="text-xs text-text-secondary">{doc.type}</span>}
                  {doc.date && <span className="text-xs text-text-secondary">{doc.date}</span>}
                </div>
              </div>
            </div>
            <a
              href={`${API_BASE}/cosium-documents/${cosiumId}/${doc.document_id}/download`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-1" /> Telecharger
              </Button>
            </a>
          </div>
        ))}
      </div>
    );
  }

  return (
    <EmptyState
      title="Aucun document"
      description="Aucun document associe a ce client dans Cosium ou en local."
    />
  );
}
