"use client";

import { useReportWebVitals } from "next/web-vitals";

/**
 * Collecte les Core Web Vitals (LCP/FID/CLS/INP/TTFB).
 * En production, envoie les metriques au backend via `sendBeacon` (non-bloquant).
 * En dev, logue dans la console.
 */
export function WebVitals() {
  useReportWebVitals((metric) => {
    if (process.env.NODE_ENV !== "production") {
      console.debug("[WebVitals]", metric.name, Math.round(metric.value), metric);
      return;
    }
    const body = JSON.stringify({
      name: metric.name,
      value: metric.value,
      id: metric.id,
      rating: metric.rating,
      path: window.location.pathname,
    });
    const endpoint = `${process.env.NEXT_PUBLIC_API_BASE_URL ?? ""}/api/v1/web-vitals`;
    if (navigator.sendBeacon) {
      navigator.sendBeacon(endpoint, new Blob([body], { type: "application/json" }));
    } else {
      fetch(endpoint, { body, method: "POST", keepalive: true, headers: { "Content-Type": "application/json" } }).catch(() => {});
    }
  });
  return null;
}
