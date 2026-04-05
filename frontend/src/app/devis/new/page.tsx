"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm, useFieldArray } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { devisCreateSchema, type DevisCreateFormData } from "@/lib/schemas/devis";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { Plus, Trash2 } from "lucide-react";

interface CaseOption {
  id: number;
  customer_name: string;
}

export default function NewDevisPage() {
  const router = useRouter();
  const [cases, setCases] = useState<CaseOption[]>([]);
  const [error, setError] = useState<string | null>(null);

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
      .catch(() => {});
  }, []);

  const watchLignes = watch("lignes");
  const watchPartSecu = watch("part_secu");
  const watchPartMutuelle = watch("part_mutuelle");

  const calcLigneHT = (l: { quantite: number; prix_unitaire_ht: number }) =>
    Math.round(l.quantite * l.prix_unitaire_ht * 100) / 100;
  const calcLigneTTC = (l: { quantite: number; prix_unitaire_ht: number; taux_tva: number }) => {
    const ht = calcLigneHT(l);
    return Math.round(ht * (1 + l.taux_tva / 100) * 100) / 100;
  };

  const totalHT = watchLignes.reduce((s, l) => s + calcLigneHT(l), 0);
  const totalTTC = watchLignes.reduce((s, l) => s + calcLigneTTC(l), 0);
  const totalTVA = Math.round((totalTTC - totalHT) * 100) / 100;
  const reste = Math.max(Math.round((totalTTC - watchPartSecu - watchPartMutuelle) * 100) / 100, 0);

  const onSubmit = async (data: DevisCreateFormData) => {
    setError(null);
    try {
      const resp = await fetchJson<{ id: number }>("/devis", {
        method: "POST",
        body: JSON.stringify(data),
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

        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary">Lignes du devis</h3>
            <Button
              type="button"
              variant="outline"
              onClick={() => append({ designation: "", quantite: 1, prix_unitaire_ht: 0, taux_tva: 20 })}
            >
              <Plus className="h-4 w-4 mr-1" /> Ajouter une ligne
            </Button>
          </div>
          {errors.lignes?.root && <p className="mb-2 text-xs text-danger">{errors.lignes.root.message}</p>}

          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th scope="col" className="pb-2 text-left font-medium text-text-secondary">Designation *</th>
                <th scope="col" className="pb-2 text-center font-medium text-text-secondary w-20">Qte</th>
                <th scope="col" className="pb-2 text-right font-medium text-text-secondary w-28">PU HT</th>
                <th scope="col" className="pb-2 text-center font-medium text-text-secondary w-20">TVA %</th>
                <th scope="col" className="pb-2 text-right font-medium text-text-secondary w-28">HT</th>
                <th scope="col" className="pb-2 text-right font-medium text-text-secondary w-28">TTC</th>
                <th scope="col" className="pb-2 w-10"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {fields.map((field, i) => {
                const l = watchLignes[i] ?? field;
                return (
                  <tr key={field.id} className="border-b border-border last:border-0">
                    <td className="py-2 pr-2">
                      <input
                        type="text"
                        {...register(`lignes.${i}.designation`)}
                        placeholder="Ex: Monture Ray-Ban"
                        className="w-full rounded-lg border border-border px-2 py-1.5 text-sm focus:border-primary focus:outline-none"
                      />
                      {errors.lignes?.[i]?.designation && (
                        <p className="mt-1 text-xs text-danger">{errors.lignes[i].designation?.message}</p>
                      )}
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        min="1"
                        {...register(`lignes.${i}.quantite`, { valueAsNumber: true })}
                        className="w-full rounded-lg border border-border px-2 py-1.5 text-sm text-center focus:border-primary focus:outline-none"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        min="0"
                        step="0.01"
                        {...register(`lignes.${i}.prix_unitaire_ht`, { valueAsNumber: true })}
                        className="w-full rounded-lg border border-border px-2 py-1.5 text-sm text-right focus:border-primary focus:outline-none"
                      />
                    </td>
                    <td className="py-2 px-1">
                      <input
                        type="number"
                        min="0"
                        max="100"
                        step="0.1"
                        {...register(`lignes.${i}.taux_tva`, { valueAsNumber: true })}
                        className="w-full rounded-lg border border-border px-2 py-1.5 text-sm text-center focus:border-primary focus:outline-none"
                      />
                    </td>
                    <td className="py-2 px-1 text-right font-medium tabular-nums">{formatMoney(calcLigneHT(l))}</td>
                    <td className="py-2 px-1 text-right font-medium tabular-nums">{formatMoney(calcLigneTTC(l))}</td>
                    <td className="py-2 pl-1">
                      <button
                        type="button"
                        onClick={() => remove(i)}
                        disabled={fields.length <= 1}
                        className="rounded p-1 text-text-secondary hover:text-danger hover:bg-red-50 disabled:opacity-30"
                        aria-label="Supprimer la ligne"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Recapitulatif</h3>
          <div className="space-y-2 text-sm max-w-xs ml-auto">
            <div className="flex justify-between">
              <span className="text-text-secondary">Total HT</span>
              <span className="font-medium tabular-nums">{formatMoney(totalHT)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">TVA</span>
              <span className="font-medium tabular-nums">{formatMoney(totalTVA)}</span>
            </div>
            <div className="flex justify-between border-t border-border pt-2">
              <span className="font-semibold">Total TTC</span>
              <span className="font-bold tabular-nums">{formatMoney(totalTTC)}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Part Secu</span>
              <span className="tabular-nums">- {formatMoney(watchPartSecu)}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Part Mutuelle</span>
              <span className="tabular-nums">- {formatMoney(watchPartMutuelle)}</span>
            </div>
            <div className="flex justify-between border-t border-border pt-2">
              <span className="font-semibold text-danger">Reste a charge</span>
              <span className="font-bold tabular-nums text-danger">{formatMoney(reste)}</span>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 rounded-xl border border-border bg-bg-card p-4 shadow-sm flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => router.push("/devis")}>
            Annuler
          </Button>
          <Button type="submit" disabled={!isValid || isSubmitting}>
            {isSubmitting ? "Creation en cours..." : "Creer le devis"}
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
