import { FileDown } from "lucide-react";
import { PERIODS, type PeriodKey, formatRelativeTime } from "../utils";

interface Props {
  period: PeriodKey;
  onChangePeriod: (p: PeriodKey) => void;
  lastUpdated: Date | null;
  onExportPDF: () => void;
  exporting: boolean;
}

export function PeriodSelector({ period, onChangePeriod, lastUpdated, onExportPDF, exporting }: Props) {
  return (
    <div className="flex items-center gap-2 mb-6 flex-wrap">
      {PERIODS.map((p) => (
        <button
          key={p.key}
          onClick={() => onChangePeriod(p.key)}
          aria-pressed={period === p.key}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors duration-150 ${
            period === p.key
              ? "bg-primary text-white"
              : "bg-bg-card text-text-secondary border border-border hover:bg-gray-100"
          }`}
        >
          {p.label}
        </button>
      ))}
      {lastUpdated && (
        <span className="text-xs text-text-secondary ml-2">
          Mis a jour {formatRelativeTime(lastUpdated)}
        </span>
      )}
      <div className="ml-auto flex items-center gap-2">
        <button
          onClick={onExportPDF}
          disabled={exporting}
          className="inline-flex items-center gap-2 rounded-lg bg-bg-card border border-border px-3 py-1.5 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
          title="Exporter le dashboard en PDF"
          aria-label="Exporter le dashboard en PDF"
        >
          <FileDown className="h-4 w-4" aria-hidden="true" />
          {exporting ? "Export en cours..." : "Exporter PDF"}
        </button>
      </div>
    </div>
  );
}
