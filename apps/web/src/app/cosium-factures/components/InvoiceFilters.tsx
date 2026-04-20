"use client";

import { SearchInput } from "@/components/ui/SearchInput";
import { TYPE_OPTIONS, SETTLED_OPTIONS } from "./invoice-columns";

interface InvoiceFiltersProps {
  typeFilter: string;
  settledFilter: string;
  dateFrom: string;
  dateTo: string;
  hasOutstandingFilter: string;
  minAmount: string;
  maxAmount: string;
  onSearch: (q: string) => void;
  onTypeChange: (value: string) => void;
  onSettledChange: (value: string) => void;
  onDateFromChange: (value: string) => void;
  onDateToChange: (value: string) => void;
  onHasOutstandingChange: (value: string) => void;
  onMinAmountChange: (value: string) => void;
  onMaxAmountChange: (value: string) => void;
  onClearDates: () => void;
}

const SELECT_CLASS =
  "rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary";

export function InvoiceFilters({
  typeFilter,
  settledFilter,
  dateFrom,
  dateTo,
  hasOutstandingFilter,
  minAmount,
  maxAmount,
  onSearch,
  onTypeChange,
  onSettledChange,
  onDateFromChange,
  onDateToChange,
  onHasOutstandingChange,
  onMinAmountChange,
  onMaxAmountChange,
  onClearDates,
}: InvoiceFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 mb-6">
      <SearchInput placeholder="Rechercher par numero ou client..." onSearch={onSearch} />
      <select
        value={typeFilter}
        onChange={(e) => onTypeChange(e.target.value)}
        className={SELECT_CLASS}
        aria-label="Filtrer par type"
      >
        {TYPE_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <select
        value={settledFilter}
        onChange={(e) => onSettledChange(e.target.value)}
        className={SELECT_CLASS}
        aria-label="Filtrer par statut"
      >
        {SETTLED_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      <div className="flex items-center gap-2">
        <label className="text-sm text-text-secondary" htmlFor="date-from">Du</label>
        <input
          id="date-from"
          type="date"
          value={dateFrom}
          onChange={(e) => onDateFromChange(e.target.value)}
          className={SELECT_CLASS}
        />
        <label className="text-sm text-text-secondary" htmlFor="date-to">au</label>
        <input
          id="date-to"
          type="date"
          value={dateTo}
          onChange={(e) => onDateToChange(e.target.value)}
          className={SELECT_CLASS}
        />
      </div>
      <select
        value={hasOutstandingFilter}
        onChange={(e) => onHasOutstandingChange(e.target.value)}
        className={SELECT_CLASS}
        aria-label="Filtrer par encours"
      >
        <option value="">Tous (encours)</option>
        <option value="true">Avec encours &gt; 0</option>
        <option value="false">Sans encours</option>
      </select>
      <div className="flex items-center gap-2">
        <input
          type="number"
          placeholder="Min EUR"
          value={minAmount}
          onChange={(e) => onMinAmountChange(e.target.value)}
          className="w-24 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Montant minimum"
        />
        <input
          type="number"
          placeholder="Max EUR"
          value={maxAmount}
          onChange={(e) => onMaxAmountChange(e.target.value)}
          className="w-24 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Montant maximum"
        />
        {(dateFrom || dateTo) && (
          <button
            onClick={onClearDates}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Effacer dates
          </button>
        )}
      </div>
    </div>
  );
}
