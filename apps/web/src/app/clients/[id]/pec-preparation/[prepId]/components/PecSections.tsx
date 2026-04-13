import { AlertTriangle, Building2, Eye, FileCheck, Package, User } from "lucide-react";

import { AlertPanel } from "@/components/pec/AlertPanel";
import { ConsolidatedFieldDisplay } from "@/components/pec/ConsolidatedFieldDisplay";
import { CorrectionTable } from "@/components/pec/CorrectionTable";
import { DocumentChecklist } from "@/components/pec/DocumentChecklist";
import { PecSection } from "@/components/pec/PecSection";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import type {
  ConsolidatedClientProfile,
  PecPreparation,
  PecPreparationDocument,
} from "@/lib/types/pec-preparation";

import {
  CORRECTION_FIELDS,
  countSectionAlerts,
  FINANCIAL_FIELDS,
  IDENTITY_FIELDS,
  MUTUELLE_FIELDS,
  sectionStatus,
} from "../utils";

interface Props {
  data: PecPreparation;
  profile: ConsolidatedClientProfile | null;
  documents: PecPreparationDocument[] | undefined;
  dismissedAlerts: Set<string>;
  onDismissAlert: (key: string) => void;
  isFieldValidated: (field: string) => boolean;
  getOriginalValue: (field: string) => string | null;
  getCorrectionReason: (field: string) => string | null;
  onValidate: (field: string) => void;
  onCorrect: (field: string, value: string, reason?: string) => void;
  onUndoCorrection: (field: string, original: string) => void;
}

export function PecSections({
  data,
  profile,
  documents,
  dismissedAlerts,
  onDismissAlert,
  isFieldValidated,
  getOriginalValue,
  getCorrectionReason,
  onValidate,
  onCorrect,
  onUndoCorrection,
}: Props) {
  const fieldProps = (fieldName: string) => ({
    fieldName,
    validated: isFieldValidated(fieldName),
    onValidate,
    onCorrect,
    onUndoCorrection,
    originalValue: getOriginalValue(fieldName),
    correctionReason: getCorrectionReason(fieldName),
  });

  const identityAlerts = countSectionAlerts(profile, IDENTITY_FIELDS);
  const mutuelleAlerts = countSectionAlerts(profile, MUTUELLE_FIELDS);
  const correctionAlerts = countSectionAlerts(profile, CORRECTION_FIELDS);
  const financialAlerts = countSectionAlerts(profile, FINANCIAL_FIELDS);

  const correctionRows = [
    { label: "Sphere", od: profile?.sphere_od ?? null, og: profile?.sphere_og ?? null },
    { label: "Cylindre", od: profile?.cylinder_od ?? null, og: profile?.cylinder_og ?? null },
    { label: "Axe", od: profile?.axis_od ?? null, og: profile?.axis_og ?? null },
    { label: "Addition", od: profile?.addition_od ?? null, og: profile?.addition_og ?? null },
  ];

  return (
    <div className="space-y-4">
      <PecSection title="Identite du patient" icon={User} status={sectionStatus(identityAlerts.errors, identityAlerts.warnings)}>
        <ConsolidatedFieldDisplay label="Nom" field={profile?.nom ?? null} {...fieldProps("nom")} />
        <ConsolidatedFieldDisplay label="Prenom" field={profile?.prenom ?? null} {...fieldProps("prenom")} />
        <ConsolidatedFieldDisplay label="Date de naissance" field={profile?.date_naissance ?? null} {...fieldProps("date_naissance")} />
        <ConsolidatedFieldDisplay label="N. Securite sociale" field={profile?.numero_secu ?? null} {...fieldProps("numero_secu")} />
      </PecSection>

      <PecSection title="Mutuelle / OCAM" icon={Building2} status={sectionStatus(mutuelleAlerts.errors, mutuelleAlerts.warnings)}>
        <ConsolidatedFieldDisplay label="Mutuelle" field={profile?.mutuelle_nom ?? null} {...fieldProps("mutuelle_nom")} />
        <ConsolidatedFieldDisplay label="N. Adherent" field={profile?.mutuelle_numero_adherent ?? null} {...fieldProps("mutuelle_numero_adherent")} />
        <ConsolidatedFieldDisplay label="Code organisme" field={profile?.mutuelle_code_organisme ?? null} {...fieldProps("mutuelle_code_organisme")} />
        <ConsolidatedFieldDisplay label="Beneficiaire" field={profile?.type_beneficiaire ?? null} {...fieldProps("type_beneficiaire")} />
        <ConsolidatedFieldDisplay label="Fin de droits" field={profile?.date_fin_droits ?? null} {...fieldProps("date_fin_droits")} />
      </PecSection>

      <PecSection title="Correction optique" icon={Eye} status={sectionStatus(correctionAlerts.errors, correctionAlerts.warnings)}>
        <CorrectionTable
          rows={correctionRows}
          prescripteur={profile?.prescripteur ?? null}
          dateOrdonnance={profile?.date_ordonnance ?? null}
        />
        {profile?.ecart_pupillaire && (
          <div className="mt-3">
            <ConsolidatedFieldDisplay label="Ecart pupillaire" field={profile.ecart_pupillaire} {...fieldProps("ecart_pupillaire")} />
          </div>
        )}
      </PecSection>

      <PecSection title="Equipement (devis)" icon={Package} status={sectionStatus(financialAlerts.errors, financialAlerts.warnings)}>
        {profile?.monture && (
          <ConsolidatedFieldDisplay label="Monture" field={profile.monture} {...fieldProps("monture")} />
        )}
        {profile?.verres && profile.verres.length > 0 && (
          <div className="space-y-1 mt-2">
            {profile.verres.map((v, i) => (
              <ConsolidatedFieldDisplay key={i} label={`Verre ${i + 1}`} field={v} {...fieldProps(`verres_${i}`)} />
            ))}
          </div>
        )}
        <div className="mt-4 pt-3 border-t border-gray-100 space-y-2">
          {profile?.montant_ttc && (
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium text-gray-700">Total TTC</span>
              <MoneyDisplay amount={Number(profile.montant_ttc.value) || 0} />
            </div>
          )}
          {profile?.part_secu && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Part Securite sociale</span>
              <MoneyDisplay amount={Number(profile.part_secu.value) || 0} />
            </div>
          )}
          {profile?.part_mutuelle && (
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Part Mutuelle</span>
              <MoneyDisplay amount={Number(profile.part_mutuelle.value) || 0} />
            </div>
          )}
          {profile?.reste_a_charge && (
            <div className="flex justify-between items-center pt-2 border-t border-gray-200">
              <span className="text-sm font-semibold text-gray-900">Reste a charge</span>
              <MoneyDisplay amount={Number(profile.reste_a_charge.value) || 0} />
            </div>
          )}
        </div>
      </PecSection>

      <PecSection title="Pieces justificatives" icon={FileCheck} status={!documents || documents.length < 3 ? "warning" : "ok"}>
        <DocumentChecklist documents={documents ?? []} />
      </PecSection>

      <PecSection title="Alertes et incoherences" icon={AlertTriangle} status={sectionStatus(data.errors_count, data.warnings_count)}>
        <AlertPanel
          alerts={profile?.alertes ?? []}
          dismissedAlerts={dismissedAlerts}
          onDismiss={onDismissAlert}
        />
      </PecSection>
    </div>
  );
}
