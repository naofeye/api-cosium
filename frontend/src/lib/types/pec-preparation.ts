// Types for PEC Preparation (assistance PEC)

export interface ConsolidatedField {
  value: string | number | null;
  source: string;
  source_label: string;
  confidence: number;
  last_updated: string | null;
}

export interface ConsolidationAlert {
  severity: "error" | "warning" | "info";
  field: string;
  message: string;
  sources: string[];
}

export interface ConsolidatedClientProfile {
  // Identity
  nom: ConsolidatedField | null;
  prenom: ConsolidatedField | null;
  date_naissance: ConsolidatedField | null;
  numero_secu: ConsolidatedField | null;

  // Mutuelle
  mutuelle_nom: ConsolidatedField | null;
  mutuelle_numero_adherent: ConsolidatedField | null;
  mutuelle_code_organisme: ConsolidatedField | null;
  type_beneficiaire: ConsolidatedField | null;
  date_fin_droits: ConsolidatedField | null;

  // Optical correction
  sphere_od: ConsolidatedField | null;
  cylinder_od: ConsolidatedField | null;
  axis_od: ConsolidatedField | null;
  addition_od: ConsolidatedField | null;
  sphere_og: ConsolidatedField | null;
  cylinder_og: ConsolidatedField | null;
  axis_og: ConsolidatedField | null;
  addition_og: ConsolidatedField | null;
  ecart_pupillaire: ConsolidatedField | null;
  prescripteur: ConsolidatedField | null;
  date_ordonnance: ConsolidatedField | null;

  // Equipment
  monture: ConsolidatedField | null;
  verres: ConsolidatedField[];

  // Financial
  montant_ttc: ConsolidatedField | null;
  part_secu: ConsolidatedField | null;
  part_mutuelle: ConsolidatedField | null;
  reste_a_charge: ConsolidatedField | null;

  // Metadata
  alertes: ConsolidationAlert[];
  champs_manquants: string[];
  score_completude: number;
  sources_utilisees: string[];
}

export interface PecPreparation {
  id: number;
  tenant_id: number;
  customer_id: number;
  devis_id: number | null;
  pec_request_id: number | null;
  status: "en_preparation" | "prete" | "soumise" | "archivee";
  completude_score: number;
  errors_count: number;
  warnings_count: number;
  consolidated_data: ConsolidatedClientProfile | null;
  user_validations: Record<string, { validated: boolean; validated_by: number; at: string }> | null;
  user_corrections: Record<string, { original: unknown; corrected: unknown; by: number; at: string }> | null;
  created_at: string | null;
  updated_at: string | null;
  created_by: number | null;
}

export interface PecPreparationSummary {
  id: number;
  customer_id: number;
  devis_id: number | null;
  status: string;
  completude_score: number;
  errors_count: number;
  warnings_count: number;
  created_at: string | null;
}

export interface PecPreparationDocument {
  id: number;
  preparation_id: number;
  document_id: number | null;
  cosium_document_id: number | null;
  document_role: string;
  extraction_id: number | null;
}
