import type { FieldStatus } from "@/lib/types/pec-preparation";

export const SOURCE_COLORS: Record<string, string> = {
  cosium: "bg-blue-100 text-blue-700",
  cosium_client: "bg-blue-100 text-blue-700",
  devis: "bg-emerald-100 text-emerald-700",
  document_ocr: "bg-orange-100 text-orange-700",
  ocr: "bg-orange-100 text-orange-700",
  manual: "bg-gray-100 text-gray-600",
};

/**
 * Border/background styling per FieldStatus.
 */
export const STATUS_STYLES: Record<FieldStatus, string> = {
  confirmed: "border-2 border-emerald-400 bg-emerald-50/30",
  extracted: "border border-blue-200 bg-white",
  deduced: "border-2 border-amber-300 bg-amber-50/20",
  missing: "border-2 border-dashed border-red-300 bg-red-50/30",
  conflict: "border-2 border-red-400 bg-red-50/20",
  manual: "border-2 border-gray-300 bg-gray-50/30",
};

export function getSourceColor(source: string): string {
  const key = Object.keys(SOURCE_COLORS).find((k) => source.toLowerCase().includes(k));
  return key ? SOURCE_COLORS[key] : "bg-gray-100 text-gray-600";
}

export function getSourceLabel(source: string, sourceLabel: string): string {
  return sourceLabel || source;
}
