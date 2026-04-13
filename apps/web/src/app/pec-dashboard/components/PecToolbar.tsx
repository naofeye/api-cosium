import { FileDown } from "lucide-react";
import { STATUS_OPTIONS } from "../types";

interface Props {
  statusFilter: string;
  onChangeStatus: (status: string) => void;
  onExport: () => void;
  exporting: boolean;
}

export function PecToolbar({ statusFilter, onChangeStatus, onExport, exporting }: Props) {
  return (
    <div className="flex items-center gap-4 mb-4">
      <label htmlFor="status-filter" className="text-sm font-medium text-text-secondary">
        Filtrer par statut
      </label>
      <select
        id="status-filter"
        value={statusFilter}
        onChange={(e) => onChangeStatus(e.target.value)}
        className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:ring-2 focus:ring-primary focus:outline-none"
      >
        {STATUS_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <div className="ml-auto">
        <button
          onClick={onExport}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-lg bg-bg-card border border-border px-3 py-2 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
          aria-label="Exporter les preparations PEC en Excel"
        >
          <FileDown className="h-4 w-4" aria-hidden="true" />
          {exporting ? "Export en cours..." : "Exporter Excel"}
        </button>
      </div>
    </div>
  );
}
