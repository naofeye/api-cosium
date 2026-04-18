"use client";

import useSWR from "swr";
import { Cloud, HardDrive } from "lucide-react";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { API_BASE } from "@/lib/api";
import { DocumentRow } from "./_cosium_documents/DocumentRow";
import {
  type CosiumDocList,
  type DocumentExtraction,
  type LocalDocList,
  formatBytes,
} from "./_cosium_documents/types";

interface TabCosiumDocumentsProps {
  cosiumId: string | number | null;
}

export function TabCosiumDocuments({ cosiumId }: TabCosiumDocumentsProps) {
  // Try local docs first (stored in MinIO)
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

  // Fetch extractions for this customer's documents
  const { data: extractionsData } = useSWR<DocumentExtraction[]>(
    cosiumId ? `/cosium-documents/${cosiumId}/extractions` : null,
  );

  // Build a map: cosium_document_id -> extraction
  const extractionMap = new Map<number, DocumentExtraction>();
  if (extractionsData) {
    for (const ext of extractionsData) {
      if (ext.cosium_document_id !== null) {
        extractionMap.set(ext.cosium_document_id, ext);
      }
    }
  }

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
        onRetry={() => {
          mutateLocal();
          mutateCosium();
        }}
      />
    );
  }

  // Render local documents (from MinIO)
  if (hasLocalDocs) {
    const extractedCount = localData.items.filter((doc) =>
      extractionMap.has(doc.cosium_document_id),
    ).length;

    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <HardDrive
            className="h-4 w-4 text-emerald-600"
            aria-label="Stockage local"
          />
          <span className="text-xs text-text-secondary">
            {localData.total} document(s) stocke(s) localement
            {extractedCount > 0 && <> &middot; {extractedCount} analyse(s)</>}
          </span>
        </div>
        {localData.items.map((doc) => {
          const extraction = extractionMap.get(doc.cosium_document_id);
          return (
            <DocumentRow
              key={doc.id}
              docKey={doc.id}
              label={doc.name || `Document ${doc.cosium_document_id}`}
              badges={
                <>
                  <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-medium">
                    Local
                  </span>
                  <span className="text-xs text-text-secondary">
                    {formatBytes(doc.size_bytes)}
                  </span>
                  <span className="text-xs text-text-secondary">{doc.content_type}</span>
                </>
              }
              downloadUrl={`${API_BASE}/cosium-documents/local/${doc.id}/download`}
              extraction={extraction}
            />
          );
        })}
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
        {cosiumData.items.map((doc) => {
          const extraction = extractionMap.get(doc.document_id);
          return (
            <DocumentRow
              key={doc.document_id}
              docKey={doc.document_id}
              label={doc.label || `Document ${doc.document_id}`}
              badges={
                <>
                  <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-medium">
                    Cosium
                  </span>
                  {doc.type && (
                    <span className="text-xs text-text-secondary">{doc.type}</span>
                  )}
                  {doc.date && (
                    <span className="text-xs text-text-secondary">{doc.date}</span>
                  )}
                </>
              }
              downloadUrl={`${API_BASE}/cosium-documents/${cosiumId}/${doc.document_id}/download`}
              extraction={extraction}
            />
          );
        })}
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
