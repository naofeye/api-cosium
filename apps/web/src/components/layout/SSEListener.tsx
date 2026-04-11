"use client";

import { useEffect } from "react";
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

  useEffect(() => {
    if (!isAuthenticated()) return;

    connectSSE((data) => {
      // Show toast notification
      toast(data.title, mapTypeToVariant(data.type));

      // Revalidate unread notification count so the badge updates in real-time
      mutate("/notifications/unread-count");

      // Revalidate notifications dropdown if open
      mutate((key: unknown) => typeof key === "string" && key.startsWith("/notifications"), undefined, {
        revalidate: true,
      });
    });

    return () => disconnectSSE();
  }, [toast, mutate]);

  return null;
}
