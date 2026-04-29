"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { X, AlertCircle } from "lucide-react";

interface CreateAvoirDialogProps {
  open: boolean;
  onClose: () => void;
  factureId: number;
  factureNumero: string;
  factureMontantTtc: number;
}

export function CreateAvoirDialog({
  open,
  onClose,
  factureId,
  factureNumero,
  factureMontantTtc,
}: CreateAvoirDialogProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [motif, setMotif] = useState("");
  const [partial, setPartial] = useState(false);
  const [montantPartiel, setMontantPartiel] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const handleClose = () => {
    setMotif("");
    setPartial(false);
    setMontantPartiel("");
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (motif.trim().length === 0) {
      toast("Le motif de l'avoir est obligatoire.", "error");
      return;
    }

    let montant_ttc_partiel: number | null = null;
    if (partial) {
      const parsed = parseFloat(montantPartiel);
      if (!Number.isFinite(parsed) || parsed <= 0) {
        toast("Le montant partiel doit etre un nombre positif.", "error");
        return;
      }
      if (parsed > factureMontantTtc) {
        toast(
          `Le montant partiel (${formatMoney(parsed)}) ne peut pas exceder la facture (${formatMoney(factureMontantTtc)}).`,
          "error",
        );
        return;
      }
      montant_ttc_partiel = parsed;
    }

    setSubmitting(true);
    try {
      const result = await fetchJson<{ id: number; numero: string }>(
        `/factures/${factureId}/avoir`,
        {
          method: "POST",
          body: JSON.stringify({ motif: motif.trim(), montant_ttc_partiel }),
        },
      );
      toast(`Avoir ${result.numero} cree.`, "success");
      handleClose();
      router.push(`/factures/${result.id}`);
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors de la creation de l'avoir.",
        "error",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Emettre un avoir"
      onKeyDown={(e) => {
        if (e.key === "Escape") handleClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-bg-card shadow-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Emettre un avoir sur {factureNumero}
          </h2>
          <button
            onClick={handleClose}
            className="rounded p-1 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Fermer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-5">
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900 flex gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
            <p>
              L&apos;avoir est une operation comptable. Il cree une nouvelle facture
              aux montants negatifs liee a {factureNumero}. La facture originale
              reste intacte.
            </p>
          </div>

          <div>
            <label
              htmlFor="avoir-motif"
              className="mb-1 block text-sm font-medium text-text-primary"
            >
              Motif de l&apos;avoir *
            </label>
            <textarea
              id="avoir-motif"
              value={motif}
              onChange={(e) => setMotif(e.target.value)}
              rows={3}
              maxLength={500}
              required
              placeholder="Retour produit, geste commercial, erreur de facturation..."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-text-secondary">
              {motif.length} / 500 caracteres
            </p>
          </div>

          <div>
            <fieldset className="space-y-2 text-sm">
              <legend className="mb-1 block font-medium text-text-primary">
                Type d&apos;avoir
              </legend>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="avoir-type"
                  checked={!partial}
                  onChange={() => setPartial(false)}
                />
                <span>
                  Avoir total — annule integralement {formatMoney(factureMontantTtc)}
                </span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  name="avoir-type"
                  checked={partial}
                  onChange={() => setPartial(true)}
                />
                <span>Avoir partiel</span>
              </label>
            </fieldset>
          </div>

          {partial && (
            <div>
              <label
                htmlFor="avoir-montant"
                className="mb-1 block text-sm font-medium text-text-primary"
              >
                Montant TTC de l&apos;avoir (EUR) *
              </label>
              <input
                id="avoir-montant"
                type="number"
                step="0.01"
                min="0.01"
                max={factureMontantTtc}
                value={montantPartiel}
                onChange={(e) => setMontantPartiel(e.target.value)}
                required={partial}
                placeholder="0.00"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
              />
              <p className="mt-1 text-xs text-text-secondary">
                Maximum : {formatMoney(factureMontantTtc)}
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 border-t border-border pt-4">
            <Button type="button" variant="outline" onClick={handleClose} disabled={submitting}>
              Annuler
            </Button>
            <Button type="submit" disabled={submitting || motif.trim().length === 0}>
              {submitting ? "Creation..." : "Creer l'avoir"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
