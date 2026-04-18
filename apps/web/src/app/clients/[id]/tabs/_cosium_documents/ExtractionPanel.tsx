import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { StructuredDataDisplay } from "./StructuredDataDisplay";
import { DOC_TYPE_COLORS, DOC_TYPE_LABELS, type DocumentExtraction } from "./types";

/**
 * Panneau déplié sous une ligne de document, affichant :
 * - badge type de document + confiance de classification
 * - données structurées (StructuredDataDisplay)
 * - texte OCR brut avec toggle show/hide
 */
export function ExtractionPanel({ extraction }: { extraction: DocumentExtraction }) {
  const [showText, setShowText] = useState(false);

  return (
    <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50/50 p-3 space-y-2">
      <div className="flex items-center gap-2 flex-wrap">
        {extraction.document_type && (
          <span
            className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
              DOC_TYPE_COLORS[extraction.document_type] ?? DOC_TYPE_COLORS.autre
            }`}
          >
            {DOC_TYPE_LABELS[extraction.document_type] ?? extraction.document_type}
          </span>
        )}
        {extraction.classification_confidence !== null && (
          <span className="text-[10px] text-text-secondary">
            Confiance : {(extraction.classification_confidence * 100).toFixed(0)} %
          </span>
        )}
        <span className="text-[10px] text-text-secondary">
          Methode : {extraction.extraction_method}
        </span>
      </div>

      {extraction.structured_data && (
        <StructuredDataDisplay data={extraction.structured_data} />
      )}

      {extraction.raw_text && (
        <div>
          <button
            onClick={() => setShowText(!showText)}
            className="flex items-center gap-1 text-xs text-primary hover:underline font-medium"
          >
            {showText ? (
              <ChevronDown className="h-3 w-3" aria-hidden="true" />
            ) : (
              <ChevronRight className="h-3 w-3" aria-hidden="true" />
            )}
            {showText ? "Masquer le texte extrait" : "Voir le texte extrait"}
          </button>
          {showText && (
            <pre className="mt-1.5 rounded-lg bg-white border border-border p-3 text-xs text-text-secondary whitespace-pre-wrap max-h-48 overflow-y-auto">
              {extraction.raw_text}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}
