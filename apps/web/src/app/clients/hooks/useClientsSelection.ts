import { useCallback, useState } from "react";

export function useClientsSelection(allIds: number[]) {
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const toggleOne = useCallback((id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === allIds.length && allIds.length > 0) return new Set();
      return new Set(allIds);
    });
  }, [allIds]);

  const clear = useCallback(() => setSelectedIds(new Set()), []);

  return { selectedIds, toggleOne, toggleAll, clear };
}
