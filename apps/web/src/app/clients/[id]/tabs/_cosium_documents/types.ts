import type { LocalCosiumDocument } from "@/lib/types";

export interface LocalDocList {
  items: LocalCosiumDocument[];
  total: number;
}

export interface CosiumDocList {
  items: Array<{
    document_id: number;
    label: string;
    type: string;
    date: string | null;
    size: number | null;
  }>;
  total: number;
}

export interface DocumentExtraction {
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

export const DOC_TYPE_LABELS: Record<string, string> = {
  ordonnance: "Ordonnance",
  devis: "Devis",
  attestation_mutuelle: "Attestation mutuelle",
  facture: "Facture",
  carte_mutuelle: "Carte mutuelle",
  courrier: "Courrier",
  autre: "Autre",
};

export const DOC_TYPE_COLORS: Record<string, string> = {
  ordonnance: "bg-blue-100 text-blue-800",
  devis: "bg-purple-100 text-purple-800",
  attestation_mutuelle: "bg-emerald-100 text-emerald-800",
  facture: "bg-amber-100 text-amber-800",
  carte_mutuelle: "bg-cyan-100 text-cyan-800",
  courrier: "bg-gray-100 text-gray-800",
  autre: "bg-gray-100 text-gray-700",
};

export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 o";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

export function formatDiopter(val: number | string | null | undefined): string {
  if (val === null || val === undefined || val === "" || val === "-") return "-";
  const n = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(n)) return String(val);
  const sign = n >= 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}`;
}
