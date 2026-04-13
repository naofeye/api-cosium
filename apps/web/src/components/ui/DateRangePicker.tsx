import { Calendar } from "lucide-react";
import { Button } from "./Button";

interface Props {
  dateFrom: string;
  dateTo: string;
  onChangeFrom: (val: string) => void;
  onChangeTo: (val: string) => void;
  onClear?: () => void;
  labelFrom?: string;
  labelTo?: string;
}

export function DateRangePicker({
  dateFrom,
  dateTo,
  onChangeFrom,
  onChangeTo,
  onClear,
  labelFrom = "Date debut",
  labelTo = "Date fin",
}: Props) {
  return (
    <div className="flex items-center gap-2">
      <Calendar className="h-4 w-4 text-gray-500" aria-hidden="true" />
      <label htmlFor="dr-from" className="sr-only">{labelFrom}</label>
      <input
        id="dr-from"
        type="date"
        value={dateFrom}
        onChange={(e) => onChangeFrom(e.target.value)}
        max={dateTo || undefined}
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
      />
      <span className="text-gray-500 text-sm">au</span>
      <label htmlFor="dr-to" className="sr-only">{labelTo}</label>
      <input
        id="dr-to"
        type="date"
        value={dateTo}
        onChange={(e) => onChangeTo(e.target.value)}
        min={dateFrom || undefined}
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500"
      />
      {(dateFrom || dateTo) && onClear && (
        <Button variant="outline" size="sm" onClick={onClear}>
          Effacer
        </Button>
      )}
    </div>
  );
}
