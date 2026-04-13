import { useState, type ChangeEvent } from "react";
import { fetchJson } from "@/lib/api";

interface Args {
  refetchTx: () => Promise<unknown>;
  refetchPayments: () => Promise<unknown>;
}

export function useRapprochementActions({ refetchTx, refetchPayments }: Args) {
  const [uploading, setUploading] = useState(false);
  const [reconciling, setReconciling] = useState(false);
  const [matching, setMatching] = useState(false);
  const [importResult, setImportResult] = useState<string | null>(null);
  const [reconcileResult, setReconcileResult] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<string | null>(null);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const upload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setImportResult(null);
    setMutationError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await fetchJson<{ imported?: number; total?: number }>(
        "/banking/import-statement",
        { method: "POST", body: formData },
      );
      setImportResult(`${data.imported ?? data.total ?? 0} transaction(s) importee(s)`);
      await refetchTx();
    } catch {
      setMutationError("Erreur lors de l'import");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const autoReconcile = async () => {
    setReconciling(true);
    setReconcileResult(null);
    setMutationError(null);
    try {
      const resp = await fetchJson<{ matched: number; unmatched: number }>(
        "/banking/reconcile",
        { method: "POST" },
      );
      await refetchTx();
      await refetchPayments();
      setReconcileResult(`${resp.matched} rapproche(s), ${resp.unmatched} non rapproche(s)`);
    } catch {
      setMutationError("Erreur lors du rapprochement");
    } finally {
      setReconciling(false);
    }
  };

  const manualMatch = async (transactionId: number, paymentId: number) => {
    setMatching(true);
    setMatchResult(null);
    setMutationError(null);
    try {
      await fetchJson("/banking/match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transaction_id: transactionId, payment_id: paymentId }),
      });
      await refetchTx();
      await refetchPayments();
      setMatchResult("Transaction rapprochee avec succes");
    } catch {
      setMutationError("Erreur lors du rapprochement manuel");
    } finally {
      setMatching(false);
    }
  };

  return {
    state: { uploading, reconciling, matching, importResult, reconcileResult, matchResult, mutationError },
    actions: { upload, autoReconcile, manualMatch },
  };
}
