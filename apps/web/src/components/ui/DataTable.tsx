"use client";

import { useState, useMemo, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, type LucideIcon } from "lucide-react";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { ErrorState } from "./ErrorState";
import { type ReactNode } from "react";
import { useColumnVisibility } from "./useColumnVisibility";
import { DataTableColumnPicker } from "./DataTableColumnPicker";

export interface Column<T> {
  key: string;
  header: string | ReactNode;
  render: (row: T) => ReactNode;
  className?: string;
  sortable?: boolean;
  /** If true, the column cannot be hidden via column customization */
  alwaysVisible?: boolean;
}

type SortDirection = "asc" | "desc";

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  onRowClick?: (row: T) => void;
  emptyTitle?: string;
  emptyDescription?: string;
  emptyIcon?: LucideIcon;
  emptyAction?: ReactNode;
  page?: number;
  pageSize?: number;
  total?: number;
  onPageChange?: (page: number) => void;
  /** Unique key for storing column visibility preference in localStorage. If omitted, column customization is disabled. */
  storageKey?: string;
}

export function DataTable<T extends { id: number | string }>({
  columns,
  data,
  loading,
  error,
  onRetry,
  onRowClick,
  emptyTitle = "Aucune donnee",
  emptyDescription = "Aucun element a afficher pour le moment.",
  emptyIcon,
  emptyAction,
  page = 1,
  pageSize = 25,
  total,
  onPageChange,
  storageKey,
}: DataTableProps<T>) {
  const safeData = data ?? [];

  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [showColumnPicker, setShowColumnPicker] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  const allColumnKeys = useMemo(() => columns.map((c) => c.key), [columns]);
  const { hiddenColumns, toggle: toggleColumn } = useColumnVisibility(storageKey, allColumnKeys);

  const visibleColumns = useMemo(
    () => columns.filter((c) => c.alwaysVisible || !hiddenColumns.has(c.key)),
    [columns, hiddenColumns],
  );

  // Close picker when clicking outside
  useEffect(() => {
    if (!showColumnPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setShowColumnPicker(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showColumnPicker]);

  const handleSort = (columnKey: string) => {
    if (sortKey === columnKey) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(columnKey);
      setSortDirection("asc");
    }
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return safeData;
    const col = visibleColumns.find((c) => c.key === sortKey);
    if (!col?.sortable) return safeData;

    return [...safeData].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];

      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;

      let cmp = 0;
      if (typeof aVal === "number" && typeof bVal === "number") {
        cmp = aVal - bVal;
      } else {
        cmp = String(aVal).localeCompare(String(bVal), "fr", { sensitivity: "base" });
      }

      return sortDirection === "asc" ? cmp : -cmp;
    });
  }, [safeData, sortKey, sortDirection, visibleColumns]);

  if (loading) return <LoadingState text="Chargement des données..." />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (safeData.length === 0) return <EmptyState title={emptyTitle} description={emptyDescription} icon={emptyIcon} action={emptyAction} />;

  const totalPages = total ? Math.ceil(total / pageSize) : 1;

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 border-border bg-gray-100/80 dark:bg-gray-800/60">
              {visibleColumns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    "px-3 sm:px-5 py-3.5 text-left text-xs font-semibold uppercase tracking-wider text-text-secondary whitespace-nowrap",
                    col.sortable && "cursor-pointer select-none hover:text-text-primary",
                    col.className,
                  )}
                  onClick={col.sortable ? () => handleSort(col.key) : undefined}
                  onKeyDown={col.sortable ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleSort(col.key); } } : undefined}
                  tabIndex={col.sortable ? 0 : undefined}
                  aria-sort={sortKey === col.key ? (sortDirection === "asc" ? "ascending" : "descending") : undefined}
                  role={col.sortable ? "columnheader" : undefined}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {col.sortable && (
                      <span className="inline-flex text-gray-400">
                        {sortKey === col.key ? (
                          sortDirection === "asc" ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )
                        ) : (
                          <ChevronsUpDown className="h-3.5 w-3.5" />
                        )}
                      </span>
                    )}
                  </span>
                </th>
              ))}
              {storageKey && (
                <DataTableColumnPicker
                  pickerRef={pickerRef}
                  showColumnPicker={showColumnPicker}
                  onTogglePicker={() => setShowColumnPicker((v) => !v)}
                  columns={columns}
                  hiddenColumns={hiddenColumns}
                  visibleCount={visibleColumns.length}
                  onToggleColumn={toggleColumn}
                />
              )}
            </tr>
          </thead>
          <tbody>
            {sortedData.map((row) => (
              <tr
                key={row.id}
                className={cn(
                  "border-b border-border last:border-0 transition-colors duration-150",
                  onRowClick && "cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50",
                )}
                tabIndex={onRowClick ? 0 : undefined}
                role={onRowClick ? "button" : undefined}
                onClick={() => onRowClick?.(row)}
                onKeyDown={onRowClick ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onRowClick(row); } } : undefined}
              >
                {visibleColumns.map((col) => (
                  <td key={col.key} className={cn("px-3 sm:px-4 py-3", col.className)}>
                    {col.render(row)}
                  </td>
                ))}
                {storageKey && <td className="px-2 py-3 w-8" />}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {onPageChange && totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between text-sm text-text-secondary">
          <span>
            Page {page} sur {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              className="rounded-lg border border-border p-2 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-gray-100 disabled:opacity-40"
              aria-label="Page précédente"
              title="Page precedente"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded-lg border border-border p-2 min-h-[44px] min-w-[44px] flex items-center justify-center hover:bg-gray-100 disabled:opacity-40"
              aria-label="Page suivante"
              title="Page suivante"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
