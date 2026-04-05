"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import useSWR from "swr";
import { cn } from "@/lib/utils";

interface AsyncSelectItem {
  [key: string]: unknown;
}

interface AsyncSelectProps {
  /** API endpoint path, e.g. "/clients" */
  endpoint: string;
  /** Key used for display label, e.g. "last_name" */
  labelKey: string;
  /** Key used as value, e.g. "id" */
  valueKey: string;
  /** Optional secondary label key, e.g. "first_name" */
  secondaryLabelKey?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Callback when an item is selected */
  onSelect: (value: number | string, item: AsyncSelectItem) => void;
  /** Additional CSS classes */
  className?: string;
  /** Minimum characters before searching (default: 2) */
  minChars?: number;
}

export function AsyncSelect({
  endpoint,
  labelKey,
  secondaryLabelKey,
  valueKey,
  placeholder = "Rechercher...",
  onSelect,
  className,
  minChars = 2,
}: AsyncSelectProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  const shouldFetch = query.length >= minChars;
  const { data, isLoading } = useSWR<{ items?: AsyncSelectItem[] } | AsyncSelectItem[]>(
    shouldFetch ? `${endpoint}?q=${encodeURIComponent(query)}&page_size=10` : null,
    { dedupingInterval: 300 },
  );

  const items: AsyncSelectItem[] = Array.isArray(data) ? data : ((data as { items?: AsyncSelectItem[] })?.items ?? []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = useCallback(
    (item: AsyncSelectItem) => {
      const label = String(item[labelKey] ?? "");
      const secondary = secondaryLabelKey ? String(item[secondaryLabelKey] ?? "") : "";
      setQuery(secondary ? `${label} ${secondary}` : label);
      setOpen(false);
      setHighlightIndex(-1);
      onSelect(item[valueKey] as number | string, item);
    },
    [labelKey, secondaryLabelKey, valueKey, onSelect],
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((prev) => (prev + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((prev) => (prev <= 0 ? items.length - 1 : prev - 1));
    } else if (e.key === "Enter" && highlightIndex >= 0) {
      e.preventDefault();
      handleSelect(items[highlightIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          setHighlightIndex(-1);
        }}
        onFocus={() => {
          if (shouldFetch) setOpen(true);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
      />
      {open && shouldFetch && (
        <ul
          className="absolute z-50 mt-1 max-h-48 w-full overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg"
          role="listbox"
        >
          {isLoading && <li className="px-4 py-3 text-sm text-gray-500">Recherche en cours...</li>}
          {!isLoading && items.length === 0 && <li className="px-4 py-3 text-sm text-gray-500">Aucun resultat</li>}
          {items.map((item, idx) => (
            <li
              key={String(item[valueKey])}
              className={cn(
                "cursor-pointer px-4 py-2.5 text-sm transition-colors",
                idx === highlightIndex ? "bg-blue-50 text-blue-700" : "hover:bg-gray-50",
              )}
              onClick={() => handleSelect(item)}
              role="option"
              aria-selected={idx === highlightIndex}
            >
              {String(item[labelKey] ?? "")}{" "}
              {secondaryLabelKey && <span className="text-gray-500">{String(item[secondaryLabelKey] ?? "")}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
