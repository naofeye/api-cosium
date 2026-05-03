"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { devisCreateSchema, type DevisCreateFormData } from "@/lib/schemas/devis";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { mutateJson } from "@/lib/mutate";
import { logger } from "@/lib/logger";
import { ClientContextPanel } from "./components/ClientContextPanel";
import type { ClientContext } from "./components/ClientContextPanel";
import { DevisLinesForm, calcLigneHT, calcLigneTTC } from "./components/DevisLinesForm";
import { DevisSummary } from "./components/DevisSummary";

interface CaseOption {
  id: number;
  customer_id?: number;
  customer_name: string;
}

export default function NewDevisPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [clientContext, setClientContext] = useState<ClientContext | null>(null);
  const [loadingContext, setLoadingContext] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting, isValid },
  } = useForm<DevisCreateFormData>({
    resolver: zodResolver(devisCreateSchema),
    mode: "onChange",
    defaultValues: {
      case_id: 0,
      part_secu: 0,
      part_mutuelle: 0,
      lignes: [{ designation: "", quantite: 1, prix_unitaire_ht: 0, taux_tva: 20 }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "lignes" });

  useEffect(() => {
    fetchJson<CaseOption[]>("/cases")
      .then(setCases)
      .catch((err) => {
        logger.error("[Devis] Impossible de charger les dossiers:", err);
      });
  }, []);

  const watchCaseId = watch("case_id");

  useEffect(() => {
    if (!watchCaseId || watchCaseId === 0) {
      setClientContext(null);
      return;
    }
    const selectedCase = cases.find((c) => c.id === watchCaseId);
    if (!selectedCase?.customer_id) {
      setClientContext(null);
      return;
    }
    const customerId = selectedCase.customer_id;
    setLoadingContext(true);
    fetchJson<{
      cosium_data?: {
        correction_actuelle: ClientContext["correction"];
        mutuelles: Array<{ mutuelle_name: string; active: boolean }>;
      } | null;
    }>(`/clients/${customerId}/360`)
      .then((data) => {
        const cd = data?.cosium_data;
        setClientContext({
          correction: cd?.correction_actuelle ?? null,
          mutuelles: cd?.mutuelles?.filter((m) => m.active) ?? [],
        });
      })
      .catch(() => setClientContext(null))
      .finally(() => setLoadingContext(false));
  }, [watchCaseId, cases]);

  const watchLignes = watch("lignes");
  const watchPartSecu = watch("part_secu");
  const watchPartMutuelle = watch("part_mutuelle");

  const totalHT = (watchLignes ?? []).reduce((s, l) => s + calcLigneHT(l), 0);
  const totalTTC = (watchLignes ?? []).reduce((s, l) => s + calcLigneTTC(l), 0);
  const totalTVA = Math.round((totalTTC - totalHT) * 100) / 100;
  const reste = Math.max(Math.round((totalTTC - (Number(watchPartSecu) || 0) - (Number(watchPartMutuelle) || 0)) * 100) / 100, 0);

  // Cle d'idempotence stable pour la duree de vie du formulaire (Codex M1) :
  // un retry sur erreur reseau ou un double clic envoie la MEME cle, ce qui
  // permet au backend de dedupliquer plutot que creer un doublon.
  const idempotencyKey = useRef(crypto.randomUUID()).current;

  const onSubmit = async (data: DevisCreateFormData) => {
    setError(null);
    try {
      const resp = await mutateJson<{ id: number }>("/devis", {
        method: "POST",
        body: JSON.stringify(data),
        idempotencyKey,
      });
      router.push(`/devis/${resp.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors de la creation du devis");
    }
  };

  return (
    <PageLayout title="Nouveau devis" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Nouveau" }]}>
      <form onSubmit={handleSubmit(onSubmit)}>
        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error}</div>
        )}

        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Informations generales</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Dossier *</label>
              <select
                {...register("case_id", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">Selectionner un dossier</option>
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    #{c.id} - {c.customer_name}
                  </option>
                ))}
              </select>
              {errors.case_id && <p className="mt-1 text-xs text-danger">{errors.case_id.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Part Secu (EUR)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                {...register("part_secu", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {errors.part_secu && <p className="mt-1 text-xs text-danger">{errors.part_secu.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-text-primary mb-1">Part Mutuelle (EUR)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                {...register("part_mutuelle", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              />
              {errors.part_mutuelle && <p className="mt-1 text-xs text-danger">{errors.part_mutuelle.message}</p>}
            </div>
          </div>
        </div>

        <ClientContextPanel clientContext={clientContext} loadingContext={loadingContext} />

        <DevisLinesForm
          fields={fields}
          watchLignes={watchLignes}
          register={register}
          errors={errors}
          onAppend={() => append({ designation: "", quantite: 1, prix_unitaire_ht: 0, taux_tva: 20 })}
          onRemove={remove}
        />

        <DevisSummary
          totalHT={totalHT}
          totalTVA={totalTVA}
          totalTTC={totalTTC}
          partSecu={Number(watchPartSecu) || 0}
          partMutuelle={Number(watchPartMutuelle) || 0}
          reste={reste}
        />

        <div className="sticky bottom-20 lg:bottom-0 rounded-xl border border-border bg-bg-card p-4 shadow-sm flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.push("/devis")}>
            Annuler
          </Button>
          <Button type="submit" disabled={!isValid} loading={isSubmitting}>
            {isSubmitting ? "Creation en cours..." : "Creer le devis"}
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
