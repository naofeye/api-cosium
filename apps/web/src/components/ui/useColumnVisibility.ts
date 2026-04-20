import { useState, useCallback } from "react";

const MIN_VISIBLE_COLUMNS = 3;

export { MIN_VISIBLE_COLUMNS };

export function useColumnVisibility(storageKey: string | undefined, _allColumnKeys: string[]) {
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(() => {
    if (!storageKey || typeof window === "undefined") return new Set();
    try {
      const stored = localStorage.getItem(`datatable-cols-${storageKey}`);
      if (stored) return new Set(JSON.parse(stored) as string[]);
    } catch {
      // ignore
    }
    return new Set();
  });

  const persist = useCallback(
    (hidden: Set<string>) => {
      if (!storageKey) return;
      try {
        localStorage.setItem(`datatable-cols-${storageKey}`, JSON.stringify([...hidden]));
      } catch {
        // ignore
      }
    },
    [storageKey],
  );

  const toggle = useCallback(
    (key: string, visibleCount: number) => {
      setHiddenColumns((prev) => {
        const next = new Set(prev);
        if (next.has(key)) {
          next.delete(key);
        } else {
          // Prevent hiding if it would drop below MIN_VISIBLE_COLUMNS
          if (visibleCount <= MIN_VISIBLE_COLUMNS) return prev;
          next.add(key);
        }
        persist(next);
        return next;
      });
    },
    [persist],
  );

  return { hiddenColumns, toggle };
}
