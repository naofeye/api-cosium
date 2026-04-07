"use client";

import { useState } from "react";
import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { API_BASE } from "@/lib/api";
import { Download, FileText, HardDrive, Cloud, ChevronDown, ChevronRight, Eye } from "lucide-react";
import type { LocalCosiumDocument, CosiumDocument } from "@/lib/types";

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

interface DocumentExtraction {
  id: number;
  document_id: number | null;
  cosium_document_id: number | null;
  raw_text: string;
  document_type: string | null;
  classification_confidence: number | null;
  extraction_method: string;
  ocr_confidence: number | null;
  structured_data: string | null;
  extracted_at: string;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  ordonnance: "Ordonnance",
  devis: "Devis",
  attestation_mutuelle: "Attestation mutuelle",
  facture: "Facture",
  carte_mutuelle: "Carte mutuelle",
  courrier: "Courrier",
  autre: "Autre",
};

const DOC_TYPE_COLORS: Record<string, string> = {
  ordonnance: "bg-blue-100 text-blue-800",
  devis: "bg-purple-100 text-purple-800",
  attestation_mutuelle: "bg-emerald-100 text-emerald-800",
  facture: "bg-amber-100 text-amber-800",
  carte_mutuelle: "bg-cyan-100 text-cyan-800",
  courrier: "bg-gray-100 text-gray-800",
  autre: "bg-gray-100 text-gray-700",
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 o";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

function formatDiopter(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === "" || val === "-") return "-";
  const n = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(n)) return String(val);
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}`;
}

function StructuredDataDisplay({ data }: { data: string }) {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(data);
  } catch {
    return <pre className="text-xs text-text-secondary whitespace-pre-wrap">{data}</pre>;
  }

  // Check if it's an ordonnance with OD/OG data
  const hasODOG =
    parsed.sphere_od !== undefined ||
    parsed.sphere_og !== undefined ||
    parsed.od_sphere !== undefined ||
    parsed.og_sphere !== undefined;

  if (hasODOG) {
    const getVal = (key: string): string => {
      const v = parsed[key];
      if (v === null || v === undefined) return "-";
      return formatDiopter(v as number);
    };

    return (
      <div className="mt-2">
        <table className="text-xs border border-border rounded-lg overflow-hidden w-full max-w-md">
          <thead>
            <tr className="bg-gray-50 text-text-secondary">
              <th className="px-3 py-1.5 text-left font-medium"></th>
              <th className="px-3 py-1.5 text-center font-medium">Sphere</th>
              <th className="px-3 py-1.5 text-center font-medium">Cylindre</th>
              <th className="px-3 py-1.5 text-center font-medium">Axe</th>
              <th className="px-3 py-1.5 text-center font-medium">Addition</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-border">
              <td className="px-3 py-1.5 font-medium text-text-primary">OD</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("sphere_od") !== "-" ? getVal("sphere_od") : getVal("od_sphere")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("cylinder_od") !== "-" ? getVal("cylinder_od") : getVal("od_cylinder")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("axis_od") !== "-" ? getVal("axis_od") : getVal("od_axis")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("addition_od") !== "-" ? getVal("addition_od") : getVal("od_addition")}</td>
            </tr>
            <tr className="border-t border-border">
              <td className="px-3 py-1.5 font-medium text-text-primary">OG</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("sphere_og") !== "-" ? getVal("sphere_og") : getVal("og_sphere")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("cylinder_og") !== "-" ? getVal("cylinder_og") : getVal("og_cylinder")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("axis_og") !== "-" ? getVal("axis_og") : getVal("og_axis")}</td>
              <td className="px-3 py-1.5 text-center tabular-nums">{getVal("addition_og") !== "-" ? getVal("addition_og") : getVal("og_addition")}</td>
            </tr>
          </tbody>
        </table>
        {typeof parsed.prescriber_name === "string" && parsed.prescriber_name && (
          <p className="text-xs text-text-secondary mt-1">
            Prescripteur : <span className="font-medium">{parsed.prescriber_name}</span>
          </p>
        )}
        {typeof parsed.prescription_date === "string" && parsed.prescription_date && (
          <p className="text-xs text-text-secondary">
            Date : {parsed.prescription_date}
          </p>
        )}
      </div>
    );
  }

  // Generic structured data display
  const entries = Object.entries(parsed).filter(
    ([, v]) => v !== null && v !== undefined && v !== ""
  );
  if (entries.length === 0) return null;

  return (
    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      {entries.map(([key, val]) => (
        <div key={key} className="flex gap-1">
          <span className="text-text-secondary">{key.replace(/_/g, " ")} :</span>
          <span className="font-medium text-text-primary">{String(val)}</span>
        </div>
      ))}
    </div>
  );
}

function ExtractionPanel({ extraction }: { extraction: DocumentExtraction }) {
  const [showText, setShowText] = useState(false);

  return (
    <div className="mt-2 rounded-lg border border-blue-200 bg-blue-50/50 p-3 space-y-2">
      {/* Document type badge + confidence */}
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

      {/* Structured data */}
      {extraction.structured_data && (
        <StructuredDataDisplay data={extraction.structured_data} />
      )}

      {/* Raw text toggle */}
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

function DocumentRow({
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
    <div
      key={docKey}
      className="rounded-lg border border-border bg-bg-card p-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <FileText className="h-5 w-5 text-text-secondary shrink-0" aria-hidden="true" />
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
              aria-label={expanded ? "Masquer le contenu extrait" : "Voir le contenu extrait"}
              aria-expanded={expanded}
            >
              <Eye className="h-4 w-4 mr-1" />
              {expanded ? "Masquer" : "Contenu"}
            </Button>
          )}
          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-1" /> Telecharger
            </Button>
          </a>
        </div>
      </div>
      {expanded && extraction && (
        <ExtractionPanel extraction={extraction} />
      )}
    </div>
  );
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

  // Fetch extractions for this customer's documents
  const {
    data: extractionsData,
  } = useSWR<DocumentExtraction[]>(
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
        onRetry={() => { mutateLocal(); mutateCosium(); }}
      />
    );
  }

  // Render local documents (from MinIO)
  if (hasLocalDocs) {
    const extractedCount = localData.items.filter(
      (doc) => extractionMap.has(doc.cosium_document_id)
    ).length;

    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 mb-3">
          <HardDrive className="h-4 w-4 text-emerald-600" aria-label="Stockage local" />
          <span className="text-xs text-text-secondary">
            {localData.total} document(s) stocke(s) localement
            {extractedCount > 0 && (
              <> &middot; {extractedCount} analyse(s)</>
            )}
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
                  <span className="inline-flex items-center rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5 text-[10px] font-medium">Local</span>
                  <span className="text-xs text-text-secondary">{formatBytes(doc.size_bytes)}</span>
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
                  <span className="inline-flex items-center rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[10px] font-medium">Cosium</span>
                  {doc.type && <span className="text-xs text-text-secondary">{doc.type}</span>}
                  {doc.date && <span className="text-xs text-text-secondary">{doc.date}</span>}
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
