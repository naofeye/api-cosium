"use client";

import { Search, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface SearchInputProps {
  placeholder?: string;
  value?: string;
  onSearch: (query: string) => void;
  className?: string;
}

export function SearchInput({ placeholder = "Rechercher...", value: controlledValue, onSearch, className }: SearchInputProps) {
  const [localValue, setLocalValue] = useState(controlledValue || "");
  const onSearchRef = useRef(onSearch);
  onSearchRef.current = onSearch;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Sync controlled value from parent
  useEffect(() => {
    if (controlledValue !== undefined) {
      setLocalValue(controlledValue);
    }
  }, [controlledValue]);

  const debouncedSearch = useCallback((val: string) => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => onSearchRef.current(val), 300);
  }, []);

  useEffect(() => {
    debouncedSearch(localValue);
    return () => clearTimeout(timeoutRef.current);
  }, [localValue, debouncedSearch]);

  return (
    <div className={cn("relative", className)}>
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
      <input
        type="text"
        value={localValue}
        onChange={(e) => setLocalValue(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        className="w-full rounded-lg border border-border bg-white py-2 pl-10 pr-8 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
      />
      {localValue && (
        <button
          onClick={() => setLocalValue("")}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
          aria-label="Effacer la recherche"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
