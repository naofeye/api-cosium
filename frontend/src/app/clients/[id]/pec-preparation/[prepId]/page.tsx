"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import Link from "next/link";
import {
  User,
  Building2,
  Eye,
  Package,
  FileCheck,
  AlertTriangle,
  RefreshCw,
  Send,
  ArrowLeft,
  FileDown,
  Copy,
  ClipboardCheck,
} from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";

import { CompletionGauge } from "@/components/pec/CompletionGauge";
import { PecSection } from "@/components/pec/PecSection";
import { ConsolidatedFieldDisplay } from "@/components/pec/ConsolidatedFieldDisplay";
import { AlertPanel } from "@/components/pec/AlertPanel";
import { CorrectionTable } from "@/components/pec/CorrectionTable";
import { DocumentChecklist } from "@/components/pec/DocumentChecklist";
import { PreControlPanel } from "@/components/pec/PreControlPanel";
import { AuditTrailModal } from "@/components/pec/AuditTrailModal";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";

import type { PecPreparation, PecPreparationDocument, ConsolidatedClientProfile, ConsolidatedField } from "@/lib/types/pec-preparation";

const STATUS_LABELS: Record<string, string> = {
  en_preparation: "En preparation",
  prete: "Prete",
  soumise: "Soumise",
  archivee: "Archivee",
};

function sectionStatus(errors: number, warnings: number): "ok" | "warning" | "error" {
  if (errors > 0) return "error";
  if (warnings > 0) return "warning";
  return "ok";
}

function countSectionAlerts(
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

function fieldValue(field: ConsolidatedField | null | undefined): string {
  if (!field || field.value === null || field.value === "") return "-";
  return String(field.value);
}

function SectionCopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <Button
      variant={copied ? "primary" : "ghost"}
      size="sm"
      onClick={handleCopy}
      aria-label={`Copier la section ${label}`}
    >
      {copied ? (
        <><ClipboardCheck className="h-3 w-3 mr-1" /> Copie !</>
      ) : (
        <><Copy className="h-3 w-3 mr-1" /> Copier</>
      )}
    </Button>
  );
}

function CopyPasteSummary({ profile }: { profile: ConsolidatedClientProfile }) {
  const [allCopied, setAllCopied] = useState(false);

  const sections = [
    {
      title: "ASSURE",
      lines: [
        `Nom: ${fieldValue(profile.nom)}`,
        `Prenom: ${fieldValue(profile.prenom)}`,
        `Date de naissance: ${fieldValue(profile.date_naissance)}`,
        `N. Securite sociale: ${fieldValue(profile.numero_secu)}`,
      ],
    },
    {
      title: "MUTUELLE",
      lines: [
        `Organisme: ${fieldValue(profile.mutuelle_nom)}`,
        `N. Adherent: ${fieldValue(profile.mutuelle_numero_adherent)}`,
        `Code AMC: ${fieldValue(profile.mutuelle_code_organisme)}`,
      ],
    },
    {
      title: "PRESCRIPTEUR",
      lines: [
        `${fieldValue(profile.prescripteur)}`,
        `Date ordonnance: ${fieldValue(profile.date_ordonnance)}`,
      ],
    },
    {
      title: "CORRECTION",
      lines: [
        `OD: Sph ${fieldValue(profile.sphere_od)}  Cyl ${fieldValue(profile.cylinder_od)}  Axe ${fieldValue(profile.axis_od)}  Add ${fieldValue(profile.addition_od)}`,
        `OG: Sph ${fieldValue(profile.sphere_og)}  Cyl ${fieldValue(profile.cylinder_og)}  Axe ${fieldValue(profile.axis_og)}  Add ${fieldValue(profile.addition_og)}`,
        `EP: ${fieldValue(profile.ecart_pupillaire)}`,
      ],
    },
    {
      title: "EQUIPEMENT",
      lines: [
        ...(profile.monture ? [`Monture: ${fieldValue(profile.monture)}`] : []),
        ...(profile.verres ?? []).map((v, i) => `Verre ${i === 0 ? "OD" : "OG"}: ${fieldValue(v)}`),
      ],
    },
    {
      title: "MONTANTS",
      lines: [
        `Total TTC: ${fieldValue(profile.montant_ttc)} EUR`,
        `Part Securite sociale: ${fieldValue(profile.part_secu)} EUR`,
        `Part Mutuelle: ${fieldValue(profile.part_mutuelle)} EUR`,
        `Reste a charge: ${fieldValue(profile.reste_a_charge)} EUR`,
      ],
    },
  ];

  const fullText = sections
    .map((s) => `=== ${s.title} ===\n${s.lines.join("\n")}`)
    .join("\n\n");

  const handleCopyAll = async () => {
    try {
      await navigator.clipboard.writeText(fullText);
      setAllCopied(true);
      setTimeout(() => setAllCopied(false), 2000);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = fullText;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setAllCopied(true);
      setTimeout(() => setAllCopied(false), 2000);
    }
  };

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5 text-blue-600" />
          <h3 className="text-sm font-semibold text-gray-900">Resume pour copier-coller</h3>
          <span className="text-xs text-gray-500">(pour saisie portail OCAM)</span>
        </div>
        <Button
          variant={allCopied ? "primary" : "outline"}
          size="sm"
          onClick={handleCopyAll}
        >
          {allCopied ? (
            <><ClipboardCheck className="h-4 w-4 mr-1" /> Copie !</>
          ) : (
            <><Copy className="h-4 w-4 mr-1" /> Copier tout</>
          )}
        </Button>
      </div>
      <div className="divide-y divide-gray-100">
        {sections.map((section) => {
          const sectionText = `=== ${section.title} ===\n${section.lines.join("\n")}`;
          return (
            <div key={section.title} className="px-4 py-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {section.title}
                </span>
                <SectionCopyButton text={sectionText} label={section.title} />
              </div>
              <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                {section.lines.join("\n")}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PecPreparationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const clientId = params.id as string;
  const prepId = params.prepId as string;

  const { data, error, isLoading, mutate } = useSWR<PecPreparation>(
    `/clients/${clientId}/pec-preparation/${prepId}`,
  );

  const { data: documents } = useSWR<PecPreparationDocument[]>(
    `/pec-preparations/${prepId}/documents`,
  );

  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());
  const [auditModalOpen, setAuditModalOpen] = useState(false);

  const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

  const handleExportPDF = async () => {
    setExporting(true);
    try {
      const resp = await fetch(`${API_BASE}/pec-preparations/${prepId}/export-pdf`, {
        credentials: "include",
      });
      if (!resp.ok) throw new Error("Erreur lors de l'export PDF");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pec_preparation_${prepId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      toast("PDF telecharge avec succes", "success");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Impossible de telecharger le PDF", "error");
    } finally {
      setExporting(false);
    }
  };

  const profile = data?.consolidated_data ?? null;
  const validations = data?.user_validations ?? {};

  const isFieldValidated = useCallback(
    (fieldName: string): boolean => {
      const v = validations as Record<string, { validated?: boolean }>;
      return v[fieldName]?.validated === true;
    },
    [validations],
  );

  const handleValidate = async (fieldName: string) => {
    try {
      await fetchJson(`/pec-preparations/${prepId}/validate-field`, {
        method: "POST",
        body: JSON.stringify({ field_name: fieldName }),
      });
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la validation", "error");
    }
  };

  const handleCorrect = async (fieldName: string, newValue: string, reason?: string) => {
    try {
      await fetchJson(`/pec-preparations/${prepId}/correct-field`, {
        method: "POST",
        body: JSON.stringify({ field_name: fieldName, new_value: newValue, reason: reason || null }),
      });
      toast("Champ corrige avec succes", "success");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la correction", "error");
    }
  };

  const handleUndoCorrection = async (fieldName: string, originalValue: string) => {
    try {
      await fetchJson(`/pec-preparations/${prepId}/correct-field`, {
        method: "POST",
        body: JSON.stringify({ field_name: fieldName, new_value: originalValue, reason: "Restauration de la valeur originale" }),
      });
      toast("Correction annulee, valeur originale restauree", "success");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la restauration", "error");
    }
  };

  const getOriginalValue = (fieldName: string): string | null => {
    const corrections = data?.user_corrections;
    if (!corrections || !corrections[fieldName]) return null;
    const orig = corrections[fieldName].original;
    return orig !== null && orig !== undefined ? String(orig) : null;
  };

  const getCorrectionReason = (fieldName: string): string | null => {
    const corrections = data?.user_corrections;
    if (!corrections || !corrections[fieldName]) return null;
    return corrections[fieldName].reason ?? null;
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetchJson(`/pec-preparations/${prepId}/refresh`, { method: "POST" });
      toast("Preparation rafraichie", "success");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors du rafraichissement", "error");
    } finally {
      setRefreshing(false);
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    try {
      await fetchJson(`/pec-preparations/${prepId}/submit`, { method: "POST" });
      toast("PEC soumise avec succes", "success");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la soumission", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDismissAlert = (alertKey: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertKey]));
  };

  if (isLoading) {
    return (
      <PageLayout
        title="Chargement..."
        breadcrumb={[
          { label: "Clients", href: "/clients" },
          { label: "Client", href: `/clients/${clientId}` },
          { label: "Assistance PEC" },
        ]}
      >
        <LoadingState text="Chargement de la preparation PEC..." />
      </PageLayout>
    );
  }

  if (error || !data) {
    return (
      <PageLayout
        title="Erreur"
        breadcrumb={[
          { label: "Clients", href: "/clients" },
          { label: "Client", href: `/clients/${clientId}` },
          { label: "Assistance PEC" },
        ]}
      >
        <ErrorState
          message={error?.message ?? "Preparation PEC introuvable."}
          onRetry={() => mutate()}
        />
      </PageLayout>
    );
  }

  const identityFields = ["nom", "prenom", "date_naissance", "numero_secu"];
  const mutuelleFields = ["mutuelle_nom", "mutuelle_numero_adherent", "mutuelle_code_organisme", "type_beneficiaire", "date_fin_droits"];
  const correctionFields = ["sphere_od", "cylinder_od", "axis_od", "addition_od", "sphere_og", "cylinder_og", "axis_og", "addition_og", "ecart_pupillaire", "prescripteur", "date_ordonnance"];
  const financialFields = ["montant_ttc", "part_secu", "part_mutuelle", "reste_a_charge"];

  const identityAlerts = countSectionAlerts(profile, identityFields);
  const mutuelleAlerts = countSectionAlerts(profile, mutuelleFields);
  const correctionAlerts = countSectionAlerts(profile, correctionFields);
  const financialAlerts = countSectionAlerts(profile, financialFields);

  const correctionRows = [
    { label: "Sphere", od: profile?.sphere_od ?? null, og: profile?.sphere_og ?? null },
    { label: "Cylindre", od: profile?.cylinder_od ?? null, og: profile?.cylinder_og ?? null },
    { label: "Axe", od: profile?.axis_od ?? null, og: profile?.axis_og ?? null },
    { label: "Addition", od: profile?.addition_od ?? null, og: profile?.addition_og ?? null },
  ];

  const canSubmit = data.errors_count === 0 && data.status === "en_preparation";

  return (
    <PageLayout
      title={`Assistance PEC #${data.id}`}
      breadcrumb={[
        { label: "Clients", href: "/clients" },
        { label: "Client", href: `/clients/${clientId}` },
        { label: `Assistance PEC #${data.id}` },
      ]}
      actions={
        <div className="flex gap-2">
          <Link href={`/clients/${clientId}`}>
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-1" /> Retour
            </Button>
          </Link>
        </div>
      }
    >
      {/* Pre-control panel */}
      <PreControlPanel
        preparationId={prepId}
        onOpenAudit={() => setAuditModalOpen(true)}
      />

      {/* Audit trail modal */}
      <AuditTrailModal
        preparationId={prepId}
        open={auditModalOpen}
        onClose={() => setAuditModalOpen(false)}
      />

      {/* Header with score and status */}
      <div className="rounded-xl border border-border bg-white shadow-sm p-5 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <StatusBadge status={data.status} label={STATUS_LABELS[data.status]} />
            {data.devis_id && (
              <span className="text-sm text-gray-500">Devis #{data.devis_id}</span>
            )}
          </div>
          <div className="flex items-center gap-4">
            {data.errors_count > 0 && (
              <span className="inline-flex items-center gap-1 text-sm font-medium text-red-700">
                <AlertTriangle className="h-4 w-4" /> {data.errors_count} erreur{data.errors_count > 1 ? "s" : ""}
              </span>
            )}
            {data.warnings_count > 0 && (
              <span className="inline-flex items-center gap-1 text-sm font-medium text-amber-700">
                <AlertTriangle className="h-4 w-4" /> {data.warnings_count} alerte{data.warnings_count > 1 ? "s" : ""}
              </span>
            )}
          </div>
        </div>
        <div className="mt-4">
          <p className="text-xs font-medium text-gray-500 mb-1">Score de completude</p>
          <CompletionGauge score={data.completude_score} />
        </div>
        {profile && profile.champs_manquants.length > 0 && (
          <p className="mt-3 text-xs text-gray-500">
            Champs manquants : {profile.champs_manquants.join(", ")}
          </p>
        )}
      </div>

      {/* Sections */}
      <div className="space-y-4">
        {/* Section 1: Identity */}
        <PecSection
          title="Identite du patient"
          icon={User}
          status={sectionStatus(identityAlerts.errors, identityAlerts.warnings)}
        >
          <ConsolidatedFieldDisplay label="Nom" field={profile?.nom ?? null} fieldName="nom" validated={isFieldValidated("nom")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("nom")} correctionReason={getCorrectionReason("nom")} />
          <ConsolidatedFieldDisplay label="Prenom" field={profile?.prenom ?? null} fieldName="prenom" validated={isFieldValidated("prenom")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("prenom")} correctionReason={getCorrectionReason("prenom")} />
          <ConsolidatedFieldDisplay label="Date de naissance" field={profile?.date_naissance ?? null} fieldName="date_naissance" validated={isFieldValidated("date_naissance")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("date_naissance")} correctionReason={getCorrectionReason("date_naissance")} />
          <ConsolidatedFieldDisplay label="N. Securite sociale" field={profile?.numero_secu ?? null} fieldName="numero_secu" validated={isFieldValidated("numero_secu")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("numero_secu")} correctionReason={getCorrectionReason("numero_secu")} />
        </PecSection>

        {/* Section 2: Mutuelle */}
        <PecSection
          title="Mutuelle / OCAM"
          icon={Building2}
          status={sectionStatus(mutuelleAlerts.errors, mutuelleAlerts.warnings)}
        >
          <ConsolidatedFieldDisplay label="Mutuelle" field={profile?.mutuelle_nom ?? null} fieldName="mutuelle_nom" validated={isFieldValidated("mutuelle_nom")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("mutuelle_nom")} correctionReason={getCorrectionReason("mutuelle_nom")} />
          <ConsolidatedFieldDisplay label="N. Adherent" field={profile?.mutuelle_numero_adherent ?? null} fieldName="mutuelle_numero_adherent" validated={isFieldValidated("mutuelle_numero_adherent")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("mutuelle_numero_adherent")} correctionReason={getCorrectionReason("mutuelle_numero_adherent")} />
          <ConsolidatedFieldDisplay label="Code organisme" field={profile?.mutuelle_code_organisme ?? null} fieldName="mutuelle_code_organisme" validated={isFieldValidated("mutuelle_code_organisme")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("mutuelle_code_organisme")} correctionReason={getCorrectionReason("mutuelle_code_organisme")} />
          <ConsolidatedFieldDisplay label="Beneficiaire" field={profile?.type_beneficiaire ?? null} fieldName="type_beneficiaire" validated={isFieldValidated("type_beneficiaire")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("type_beneficiaire")} correctionReason={getCorrectionReason("type_beneficiaire")} />
          <ConsolidatedFieldDisplay label="Fin de droits" field={profile?.date_fin_droits ?? null} fieldName="date_fin_droits" validated={isFieldValidated("date_fin_droits")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("date_fin_droits")} correctionReason={getCorrectionReason("date_fin_droits")} />
        </PecSection>

        {/* Section 3: Optical Correction */}
        <PecSection
          title="Correction optique"
          icon={Eye}
          status={sectionStatus(correctionAlerts.errors, correctionAlerts.warnings)}
        >
          <CorrectionTable
            rows={correctionRows}
            prescripteur={profile?.prescripteur ?? null}
            dateOrdonnance={profile?.date_ordonnance ?? null}
          />
          {profile?.ecart_pupillaire && (
            <div className="mt-3">
              <ConsolidatedFieldDisplay label="Ecart pupillaire" field={profile.ecart_pupillaire} fieldName="ecart_pupillaire" validated={isFieldValidated("ecart_pupillaire")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("ecart_pupillaire")} correctionReason={getCorrectionReason("ecart_pupillaire")} />
            </div>
          )}
        </PecSection>

        {/* Section 4: Equipment / Devis */}
        <PecSection
          title="Equipement (devis)"
          icon={Package}
          status={sectionStatus(financialAlerts.errors, financialAlerts.warnings)}
        >
          {profile?.monture && (
            <ConsolidatedFieldDisplay label="Monture" field={profile.monture} fieldName="monture" validated={isFieldValidated("monture")} onValidate={handleValidate} onCorrect={handleCorrect} onUndoCorrection={handleUndoCorrection} originalValue={getOriginalValue("monture")} correctionReason={getCorrectionReason("monture")} />
          )}
          {profile?.verres && profile.verres.length > 0 && (
            <div className="space-y-1 mt-2">
              {profile.verres.map((v, i) => (
                <ConsolidatedFieldDisplay
                  key={i}
                  label={`Verre ${i + 1}`}
                  field={v}
                  fieldName={`verres_${i}`}
                  validated={isFieldValidated(`verres_${i}`)}
                  onValidate={handleValidate}
                  onCorrect={handleCorrect}
                  onUndoCorrection={handleUndoCorrection}
                  originalValue={getOriginalValue(`verres_${i}`)}
                  correctionReason={getCorrectionReason(`verres_${i}`)}
                />
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

        {/* Section 5: Documents */}
        <PecSection
          title="Pieces justificatives"
          icon={FileCheck}
          status={!documents || documents.length < 3 ? "warning" : "ok"}
        >
          <DocumentChecklist documents={documents ?? []} />
        </PecSection>

        {/* Section 6: Alerts */}
        <PecSection
          title="Alertes et incoherences"
          icon={AlertTriangle}
          status={sectionStatus(data.errors_count, data.warnings_count)}
        >
          <AlertPanel
            alerts={profile?.alertes ?? []}
            dismissedAlerts={dismissedAlerts}
            onDismiss={handleDismissAlert}
          />
        </PecSection>
      </div>

      {/* Resume copier-coller */}
      {profile && (
        <CopyPasteSummary profile={profile} />
      )}

      {/* Action bar */}
      <div className="sticky bottom-0 bg-white border-t border-gray-200 mt-6 p-4 flex justify-between items-center rounded-b-xl shadow-sm">
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleRefresh} loading={refreshing}>
            <RefreshCw className="h-4 w-4 mr-1" /> Rafraichir
          </Button>
          <Button variant="outline" onClick={handleExportPDF} loading={exporting}>
            <FileDown className="h-4 w-4 mr-1" /> Exporter PDF
          </Button>
        </div>
        <div className="flex gap-2">
          <Link href={`/clients/${clientId}`}>
            <Button variant="ghost">Annuler</Button>
          </Link>
          <Button
            variant="primary"
            onClick={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
            title={!canSubmit ? "Corrigez toutes les erreurs avant de soumettre" : "Soumettre la PEC"}
          >
            <Send className="h-4 w-4 mr-1" /> Soumettre la PEC
          </Button>
        </div>
      </div>
    </PageLayout>
  );
}
