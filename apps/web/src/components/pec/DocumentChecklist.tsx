"use client";

import { CheckCircle2, XCircle, FileText, Plus, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { PecPreparationDocument } from "@/lib/types/pec-preparation";

interface RequiredDocument {
  role: string;
  label: string;
}

interface DocumentChecklistProps {
  documents: PecPreparationDocument[];
  /** Optionally provide names for document roles */
  documentNames?: Record<number, string>;
  onAddDocument?: () => void;
  onViewDocument?: (docId: number) => void;
}

const REQUIRED_DOCS: RequiredDocument[] = [
  { role: "ordonnance", label: "Ordonnance" },
  { role: "devis", label: "Devis signe" },
  { role: "attestation_mutuelle", label: "Attestation mutuelle" },
];

export function DocumentChecklist({
  documents,
  documentNames,
  onAddDocument,
  onViewDocument,
}: DocumentChecklistProps) {
  const docsByRole = new Map<string, PecPreparationDocument[]>();
  for (const doc of documents) {
    const existing = docsByRole.get(doc.document_role) ?? [];
    existing.push(doc);
    docsByRole.set(doc.document_role, existing);
  }

  return (
    <div className="space-y-2">
      {REQUIRED_DOCS.map((req) => {
        const docs = docsByRole.get(req.role);
        const present = docs && docs.length > 0;

        return (
          <div key={req.role} className={cn("flex items-center justify-between py-2 px-3 rounded-lg", present ? "bg-emerald-50" : "bg-red-50")}>
            <div className="flex items-center gap-2">
              {present ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" aria-label="Present" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" aria-label="Manquant" />
              )}
              <span className={cn("text-sm font-medium", present ? "text-emerald-800" : "text-red-800")}>
                {req.label}
              </span>
              {present && docs[0].document_id && documentNames?.[docs[0].document_id] && (
                <span className="text-xs text-gray-500 ml-2">
                  {documentNames[docs[0].document_id]}
                </span>
              )}
            </div>
            {present && docs[0].document_id && onViewDocument && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => onViewDocument(docs[0].document_id!)}
                aria-label={`Voir ${req.label}`}
              >
                <Eye className="h-3 w-3 mr-1" /> Voir
              </Button>
            )}
            {!present && (
              <span className="text-xs text-red-600 font-medium uppercase">Manquant</span>
            )}
          </div>
        );
      })}

      {/* Additional (non-required) documents */}
      {documents
        .filter((d) => !REQUIRED_DOCS.some((r) => r.role === d.document_role))
        .map((doc) => (
          <div key={doc.id} className="flex items-center justify-between py-2 px-3 rounded-lg bg-gray-50">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-gray-400" aria-hidden="true" />
              <span className="text-sm text-gray-700">{doc.document_role}</span>
            </div>
            {doc.document_id && onViewDocument && (
              <Button size="sm" variant="ghost" onClick={() => onViewDocument(doc.document_id!)} aria-label="Voir le document">
                <Eye className="h-3 w-3 mr-1" /> Voir
              </Button>
            )}
          </div>
        ))}

      {onAddDocument && (
        <Button variant="outline" size="sm" onClick={onAddDocument} className="mt-3">
          <Plus className="h-4 w-4 mr-1" /> Ajouter un document
        </Button>
      )}
    </div>
  );
}
