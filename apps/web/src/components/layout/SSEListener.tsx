"use client";

import { useEffect, useRef } from "react";
import { useSWRConfig } from "swr";
import { connectSSE, disconnectSSE } from "@/lib/sse";
import { useToast } from "@/components/ui/Toast";
import { isAuthenticated } from "@/lib/auth";

type ToastVariant = "success" | "warning" | "info";

function mapTypeToVariant(type: string): ToastVariant {
  if (type === "success") return "success";
  if (type === "warning") return "warning";
  return "info";
}

export function SSEListener() {
  const { toast } = useToast();
  const { mutate } = useSWRConfig();

  // Refs stables : les hooks `toast`/`mutate` peuvent changer d'identite a
  // chaque render des Providers parents, ce qui re-declenchait connectSSE
  // et creait des connexions en double avant le cleanup. Avec des refs +
  // empty deps, on garde une seule connexion SSE pour la duree de vie du
  // composant.
  const toastRef = useRef(toast);
  const mutateRef = useRef(mutate);
  toastRef.current = toast;
  mutateRef.current = mutate;

  useEffect(() => {
    if (!isAuthenticated()) return;

    connectSSE((data) => {
      toastRef.current(data.title, mapTypeToVariant(data.type));
      mutateRef.current("/notifications/unread-count");
      mutateRef.current(
        (key: unknown) => typeof key === "string" && key.startsWith("/notifications"),
        undefined,
        { revalidate: true },
      );
    });

    return () => disconnectSSE();
  }, []);

  return null;
}
