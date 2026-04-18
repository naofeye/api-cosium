import { useState } from "react";
import { Download, Eye, FileText } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { ExtractionPanel } from "./ExtractionPanel";
import { DOC_TYPE_COLORS, DOC_TYPE_LABELS, type DocumentExtraction } from "./types";

/**
 * Ligne d'un document Cosium avec bouton download + expand extraction.
 * Utilisée à la fois pour les documents locaux (MinIO) et les documents
 * proxyés depuis Cosium.
 */
export function DocumentRow({
  docKey,
  label,
  badges,
  downloadUrl,
  extraction,
}: {
  docKey: string | number;
  label: string;
  badges: React.ReactNode;
  downloadUrl: string;
  extraction?: DocumentExtraction;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div key={docKey} className="rounded-lg border border-border bg-bg-card p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <FileText
            className="h-5 w-5 text-text-secondary shrink-0"
            aria-hidden="true"
          />
          <div className="min-w-0">
            <span className="text-sm font-medium text-text-primary truncate block">
              {label}
            </span>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              {badges}
              {extraction?.document_type && (
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    DOC_TYPE_COLORS[extraction.document_type] ?? DOC_TYPE_COLORS.autre
                  }`}
                >
                  {DOC_TYPE_LABELS[extraction.document_type] ?? extraction.document_type}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {extraction && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setExpanded(!expanded)}
              aria-label={
                expanded ? "Masquer le contenu extrait" : "Voir le contenu extrait"
              }
              aria-expanded={expanded}
            >
              <Eye className="h-4 w-4 mr-1" />
              {expanded ? "Masquer" : "Contenu"}
            </Button>
          )}
          <a href={downloadUrl} target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" /> Telecharger
            </Button>
          </a>
        </div>
      </div>
      {expanded && extraction && <ExtractionPanel extraction={extraction} />}
    </div>
  );
}
