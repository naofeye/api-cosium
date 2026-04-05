"use client";

import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Download, FileText } from "lucide-react";
import type { CosiumDocument } from "@/lib/types";

interface TabCosiumDocumentsProps {
  cosiumId: string | number | null;
}

export function TabCosiumDocuments({ cosiumId }: TabCosiumDocumentsProps) {
  const { data, error, isLoading, mutate } = useSWR<CosiumDocument[]>(
    cosiumId ? `/cosium-documents/${cosiumId}` : null,
  );

  if (!cosiumId) {
    return (
      <EmptyState
        title="Client non lie a Cosium"
        description="Ce client n'a pas d'identifiant Cosium. Les documents ne peuvent pas etre recuperes."
      />
    );
  }

  if (isLoading) return <LoadingState text="Chargement des documents Cosium..." />;
  if (error) return <ErrorState message={error.message ?? "Erreur de chargement"} onRetry={() => mutate()} />;
  if (!data || data.length === 0) {
    return (
      <EmptyState
        title="Aucun document Cosium"
        description="Aucun document associe a ce client dans Cosium."
      />
    );
  }

  return (
    <div className="space-y-2">
      {data.map((doc) => (
        <div
          key={doc.id}
          className="flex items-center justify-between rounded-lg border border-border bg-bg-card p-4"
        >
          <div className="flex items-center gap-3">
            <FileText className="h-5 w-5 text-text-secondary" aria-hidden="true" />
            <span className="text-sm font-medium text-text-primary">{doc.name}</span>
          </div>
          {doc.download_url && (
            <a href={doc.download_url} target="_blank" rel="noopener noreferrer">
              <Button variant="outline" size="sm">
                <Download className="h-4 w-4 mr-1" /> Telecharger
              </Button>
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
