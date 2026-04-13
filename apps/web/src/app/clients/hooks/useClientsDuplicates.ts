import { useCallback, useState, useTransition } from "react";
import { fetchJson } from "@/lib/api";
import type { DuplicateGroup } from "../components/DuplicatesPanel";

export function useClientsDuplicates(onError: (msg: string) => void) {
  const [show, setShow] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [pending, startTransition] = useTransition();

  const toggle = useCallback(() => {
    if (show) {
      setShow(false);
      return;
    }
    startTransition(async () => {
      try {
        const result = await fetchJson<DuplicateGroup[]>("/clients/duplicates");
        setDuplicates(result);
        setShow(true);
      } catch (err) {
        onError(err instanceof Error ? err.message : "Erreur");
        setShow(false);
        setDuplicates([]);
      }
    });
  }, [show, onError]);

  const refresh = useCallback(async () => {
    try {
      const updated = await fetchJson<DuplicateGroup[]>("/clients/duplicates");
      setDuplicates(updated);
    } catch {
      setShow(false);
    }
  }, []);

  return { show, duplicates, pending, toggle, refresh };
}
