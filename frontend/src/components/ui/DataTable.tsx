"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ChevronsUpDown, type LucideIcon } from "lucide-react";
import { EmptyState } from "./EmptyState";
import { LoadingState } from "./LoadingState";
import { ErrorState } from "./ErrorState";
import { type ReactNode } from "react";

export interface Column<T> {
  key: string;
  header: string;
  render: (row: T) => ReactNode;
  className?: string;
  sortable?: boolean;
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
}

export function DataTable<T extends { id: number | string }>({
  columns,
  data,
  loading,
  error,
  onRetry,
  onRowClick,
  emptyTitle = "Aucune donnée",
  emptyDescription = "Aucun élément à afficher pour le moment.",
  emptyIcon,
  emptyAction,
  page = 1,
  pageSize = 25,
  total,
  onPageChange,
}: DataTableProps<T>) {
  const safeData = data ?? [];

  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

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
    const col = columns.find((c) => c.key === sortKey);
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
  }, [safeData, sortKey, sortDirection, columns]);

  if (loading) return <LoadingState text="Chargement des données..." />;
  if (error) return <ErrorState message={error} onRetry={onRetry} />;
  if (safeData.length === 0) return <EmptyState title={emptyTitle} description={emptyDescription} icon={emptyIcon} action={emptyAction} />;

  const totalPages = total ? Math.ceil(total / pageSize) : 1;

  return (
    <div>
      <div className="overflow-x-auto rounded-xl border border-border bg-bg-card">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50 dark:bg-gray-800/50">
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  className={cn(
                    "px-4 py-3 text-left font-medium text-text-secondary",
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
                onClick={() => onRowClick?.(row)}
              >
                {columns.map((col) => (
                  <td key={col.key} className={cn("px-4 py-3", col.className)}>
                    {col.render(row)}
                  </td>
                ))}
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
              className="rounded-lg border border-border p-1.5 hover:bg-gray-100 disabled:opacity-40"
              aria-label="Page précédente"
              title="Page precedente"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="rounded-lg border border-border p-1.5 hover:bg-gray-100 disabled:opacity-40"
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
