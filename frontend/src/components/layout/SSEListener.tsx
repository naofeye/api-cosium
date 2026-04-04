"use client";

import { useEffect } from "react";
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

  useEffect(() => {
    if (!isAuthenticated()) return;

    connectSSE((data) => {
      toast(data.title, mapTypeToVariant(data.type));
    });

    return () => disconnectSSE();
  }, [toast]);

  return null;
}
