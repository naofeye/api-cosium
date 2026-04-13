import type { ConsolidatedClientProfile, ConsolidatedField } from "@/lib/types/pec-preparation";

export const STATUS_LABELS: Record<string, string> = {
  en_preparation: "En preparation",
  prete: "Prete",
  soumise: "Soumise",
  archivee: "Archivee",
};

export function sectionStatus(errors: number, warnings: number): "ok" | "warning" | "error" {
  if (errors > 0) return "error";
  if (warnings > 0) return "warning";
  return "ok";
}

export function countSectionAlerts(
  profile: ConsolidatedClientProfile | null,
  fields: string[],
): { errors: number; warnings: number } {
  if (!profile) return { errors: 0, warnings: 0 };
  let errors = 0;
  let warnings = 0;
  for (const alert of profile.alertes) {
    if (fields.includes(alert.field)) {
      if (alert.severity === "error") errors++;
      else if (alert.severity === "warning") warnings++;
    }
  }
  return { errors, warnings };
}

export function fieldValue(field: ConsolidatedField | null | undefined): string {
  if (!field || field.value === null || field.value === "") return "-";
  return String(field.value);
}

export const IDENTITY_FIELDS = ["nom", "prenom", "date_naissance", "numero_secu"];
export const MUTUELLE_FIELDS = ["mutuelle_nom", "mutuelle_numero_adherent", "mutuelle_code_organisme", "type_beneficiaire", "date_fin_droits"];
export const CORRECTION_FIELDS = ["sphere_od", "cylinder_od", "axis_od", "addition_od", "sphere_og", "cylinder_og", "axis_og", "addition_og", "ecart_pupillaire", "prescripteur", "date_ordonnance"];
export const FINANCIAL_FIELDS = ["montant_ttc", "part_secu", "part_mutuelle", "reste_a_charge"];
