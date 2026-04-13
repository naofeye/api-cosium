import type { ChangeEvent } from "react";
import { Calendar, RefreshCw, Upload } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface Props {
  uploading: boolean;
  reconciling: boolean;
  showReconciled: boolean | undefined;
  dateFrom: string;
  dateTo: string;
  onUpload: (e: ChangeEvent<HTMLInputElement>) => void;
  onAutoReconcile: () => void;
  onChangeReconciled: (val: boolean | undefined) => void;
  onChangeDateFrom: (val: string) => void;
  onChangeDateTo: (val: string) => void;
  onClearDates: () => void;
}

export function RapprochementToolbar({
  uploading,
  reconciling,
  showReconciled,
  dateFrom,
  dateTo,
  onUpload,
  onAutoReconcile,
  onChangeReconciled,
  onChangeDateFrom,
  onChangeDateTo,
  onClearDates,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-3 mb-6">
      <label className="cursor-pointer">
        <input type="file" accept=".csv" onChange={onUpload} className="hidden" />
        <span className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-bg-card px-4 py-2 text-sm font-medium hover:bg-gray-50 transition-colors">
          <Upload className="h-4 w-4" aria-hidden="true" />
          {uploading ? "Import en cours..." : "Importer un releve CSV"}
        </span>
      </label>

      <Button variant="outline" onClick={onAutoReconcile} disabled={reconciling}>
        <RefreshCw className={`h-4 w-4 mr-1.5 ${reconciling ? "animate-spin" : ""}`} aria-hidden="true" />
        {reconciling ? "Rapprochement..." : "Rapprochement auto"}
      </Button>

      <div className="h-6 w-px bg-gray-200 mx-1" />

      <label htmlFor="filter-reconciled" className="sr-only">Filtrer par statut de rapprochement</label>
      <select
        id="filter-reconciled"
        value={showReconciled === undefined ? "" : String(showReconciled)}
        onChange={(e) =>
          onChangeReconciled(e.target.value === "" ? undefined : e.target.value === "true")
        }
        className="rounded-lg border border-border px-3 py-2 text-sm"
      >
        <option value="">Toutes</option>
        <option value="false">Non rapprochees</option>
        <option value="true">Rapprochees</option>
      </select>

      <div className="flex items-center gap-2">
        <Calendar className="h-4 w-4 text-text-secondary" aria-hidden="true" />
        <label htmlFor="date-from" className="sr-only">Date debut</label>
        <input
          id="date-from"
          type="date"
          value={dateFrom}
          onChange={(e) => onChangeDateFrom(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        />
        <span className="text-text-secondary text-sm">au</span>
        <label htmlFor="date-to" className="sr-only">Date fin</label>
        <input
          id="date-to"
          type="date"
          value={dateTo}
          onChange={(e) => onChangeDateTo(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        />
        {(dateFrom || dateTo) && (
          <Button variant="outline" size="sm" onClick={onClearDates}>
            Effacer
          </Button>
        )}
      </div>
    </div>
  );
}
