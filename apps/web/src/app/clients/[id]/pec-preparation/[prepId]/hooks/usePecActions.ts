import { useCallback, useState } from "react";
import { useToast } from "@/components/ui/Toast";
import { fetchJson, API_BASE } from "@/lib/api";
import type { PecPreparation } from "@/lib/types/pec-preparation";

interface Args {
  prepId: string;
  data: PecPreparation | undefined;
  mutate: () => void;
}

export function usePecActions({ prepId, data, mutate }: Args) {
  const { toast } = useToast();
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pendingCorrections, setPendingCorrections] = useState(0);

  const validations = data?.user_validations ?? {};

  const isFieldValidated = useCallback(
    (fieldName: string): boolean => {
      const v = validations as Record<string, { validated?: boolean }>;
      return v[fieldName]?.validated === true;
    },
    [validations],
  );

  const getOriginalValue = useCallback((fieldName: string): string | null => {
    const corrections = data?.user_corrections;
    if (!corrections || !corrections[fieldName]) return null;
    const orig = corrections[fieldName].original;
    return orig !== null && orig !== undefined ? String(orig) : null;
  }, [data]);

  const getCorrectionReason = useCallback((fieldName: string): string | null => {
    const corrections = data?.user_corrections;
    if (!corrections || !corrections[fieldName]) return null;
    return corrections[fieldName].reason ?? null;
  }, [data]);

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
      setPendingCorrections((c) => c + 1);
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la correction", "error");
    }
  };

  const handleUndoCorrection = async (fieldName: string, originalValue: string) => {
    try {
      await fetchJson(`/pec-preparations/${prepId}/correct-field`, {
        method: "POST",
        body: JSON.stringify({
          field_name: fieldName,
          new_value: originalValue,
          reason: "Restauration de la valeur originale",
        }),
      });
      toast("Correction annulee, valeur originale restauree", "success");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la restauration", "error");
    }
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
      setPendingCorrections(0);
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur lors de la soumission", "error");
    } finally {
      setSubmitting(false);
    }
  };

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

  return {
    state: { refreshing, submitting, exporting, pendingCorrections },
    helpers: { isFieldValidated, getOriginalValue, getCorrectionReason },
    actions: { handleValidate, handleCorrect, handleUndoCorrection, handleRefresh, handleSubmit, handleExportPDF },
  };
}
