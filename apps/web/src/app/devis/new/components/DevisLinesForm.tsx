import { UseFormRegister, FieldErrors, UseFieldArrayReturn } from "react-hook-form";
import { Button } from "@/components/ui/Button";
import { formatMoney } from "@/lib/format";
import { Plus, Trash2 } from "lucide-react";
import type { DevisCreateFormData } from "@/lib/schemas/devis";

interface LigneValues {
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
}

export function calcLigneHT(l: { quantite: number; prix_unitaire_ht: number }): number {
  return Math.round((Number(l.quantite) || 0) * (Number(l.prix_unitaire_ht) || 0) * 100) / 100;
}

export function calcLigneTTC(l: LigneValues): number {
  const ht = calcLigneHT(l);
  return Math.round(ht * (1 + (Number(l.taux_tva) || 0) / 100) * 100) / 100;
}

interface DevisLinesFormProps {
  fields: UseFieldArrayReturn<DevisCreateFormData, "lignes">["fields"];
  watchLignes: DevisCreateFormData["lignes"];
  register: UseFormRegister<DevisCreateFormData>;
  errors: FieldErrors<DevisCreateFormData>;
  onAppend: () => void;
  onRemove: (index: number) => void;
}

export function DevisLinesForm({
  fields,
  watchLignes,
  register,
  errors,
  onAppend,
  onRemove,
}: DevisLinesFormProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-text-primary">Lignes du devis</h3>
        <Button type="button" variant="outline" onClick={onAppend}>
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
                    onClick={() => onRemove(i)}
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
  );
}
