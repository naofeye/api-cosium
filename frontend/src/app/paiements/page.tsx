"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { logger } from "@/lib/logger";
import { paymentCreateSchema, type PaymentCreateFormData } from "@/lib/schemas/payment";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { Plus, CheckCircle } from "lucide-react";

interface CaseOption {
  id: number;
  customer_name: string;
}

export default function PaiementsPage() {
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isValid },
  } = useForm<PaymentCreateFormData>({
    resolver: zodResolver(paymentCreateSchema),
    mode: "onChange",
    defaultValues: {
      case_id: 0,
      payer_type: "client",
      mode_paiement: "cb",
      amount_due: 0,
      amount_paid: 0,
    },
  });

  useEffect(() => {
    fetchJson<CaseOption[]>("/cases")
      .then(setCases)
      .catch((err) => {
        logger.error("[Paiements] Erreur chargement des dossiers:", err);
      });
  }, []);

  const onSubmit = async (data: PaymentCreateFormData) => {
    setError(null);
    setSuccess(null);
    try {
      const resp = await fetchJson<{ id: number; status: string }>("/paiements", {
        method: "POST",
        body: JSON.stringify({
          case_id: data.case_id,
          payer_type: data.payer_type,
          mode_paiement: data.mode_paiement,
          amount_due: data.amount_due,
          amount_paid: data.amount_paid,
        }),
      });
      setSuccess(`Paiement #${resp.id} enregistre (${resp.status})`);
      reset();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    }
  };

  return (
    <PageLayout
      title="Enregistrer un paiement"
      description="Saisie des paiements recus"
      breadcrumb={[{ label: "Paiements" }]}
    >
      {success && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="h-4 w-4" /> {success}
        </div>
      )}
      {error && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>}

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Dossier *</label>
              <select
                {...register("case_id", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              >
                <option value="">Selectionner</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.id} - {c.customer_name}
                  </option>
                ))}
              </select>
              {errors.case_id && <p className="mt-1 text-xs text-danger">{errors.case_id.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Type payeur *</label>
              <select {...register("payer_type")} className="w-full rounded-lg border border-border px-3 py-2 text-sm">
                <option value="client">Client</option>
                <option value="mutuelle">Mutuelle</option>
                <option value="secu">Securite sociale</option>
              </select>
              {errors.payer_type && <p className="mt-1 text-xs text-danger">{errors.payer_type.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Mode de paiement</label>
              <select
                {...register("mode_paiement")}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              >
                <option value="cb">Carte bancaire</option>
                <option value="virement">Virement</option>
                <option value="cheque">Cheque</option>
                <option value="especes">Especes</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Montant du (EUR)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                {...register("amount_due", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              {errors.amount_due && <p className="mt-1 text-xs text-danger">{errors.amount_due.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Montant paye (EUR) *</label>
              <input
                type="number"
                min="0"
                step="0.01"
                {...register("amount_paid", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              {errors.amount_paid && <p className="mt-1 text-xs text-danger">{errors.amount_paid.message}</p>}
            </div>
          </div>
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={!isValid || isSubmitting}>
            <Plus className="h-4 w-4 mr-1" />
            {isSubmitting ? "Enregistrement..." : "Enregistrer le paiement"}
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
