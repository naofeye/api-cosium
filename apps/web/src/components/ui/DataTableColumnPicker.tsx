"use client";

import { cn } from "@/lib/utils";
import { Settings2 } from "lucide-react";
import { type ReactNode } from "react";
import { MIN_VISIBLE_COLUMNS } from "./useColumnVisibility";

export interface ColumnPickerColumn {
  key: string;
  header: string | ReactNode;
  alwaysVisible?: boolean;
}

interface DataTableColumnPickerProps {
  pickerRef: React.RefObject<HTMLDivElement | null>;
  showColumnPicker: boolean;
  onTogglePicker: () => void;
  columns: ColumnPickerColumn[];
  hiddenColumns: Set<string>;
  visibleCount: number;
  onToggleColumn: (key: string, visibleCount: number) => void;
}

export function DataTableColumnPicker({
  pickerRef,
  showColumnPicker,
  onTogglePicker,
  columns,
  hiddenColumns,
  visibleCount,
  onToggleColumn,
}: DataTableColumnPickerProps) {
  return (
    <th scope="col" className="px-2 py-3 w-8 text-right relative">
      <div ref={pickerRef} className="inline-block">
        <button
          type="button"
          onClick={onTogglePicker}
          className="rounded p-1 text-text-secondary hover:text-text-primary hover:bg-gray-200 transition-colors"
          aria-label="Personnaliser les colonnes"
          title="Personnaliser les colonnes"
        >
          <Settings2 className="h-3.5 w-3.5" />
        </button>
        {showColumnPicker && (
          <div className="absolute right-0 top-full mt-1 z-50 w-56 rounded-lg border border-border bg-bg-card shadow-lg py-1">
            <p className="px-3 py-1.5 text-xs font-medium text-text-secondary border-b border-border">
              Colonnes visibles
            </p>
            {columns.map((col) => {
              const isHidden = hiddenColumns.has(col.key);
              const isAlwaysVisible = col.alwaysVisible === true;
              const wouldDropBelowMin = !isHidden && visibleCount <= MIN_VISIBLE_COLUMNS;
              const disabled = isAlwaysVisible || wouldDropBelowMin;
              return (
                <label
                  key={col.key}
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50",
                    disabled && "opacity-50 cursor-not-allowed",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={!isHidden}
                    disabled={disabled}
                    onChange={() => onToggleColumn(col.key, visibleCount)}
                    className="rounded border-gray-300 text-primary focus:ring-primary"
                  />
                  <span className="truncate">
                    {typeof col.header === "string" ? col.header : col.key}
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>
    </th>
  );
}
