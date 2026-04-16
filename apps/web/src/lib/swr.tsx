"use client";

import { SWRConfig } from "swr";
import { fetchJson } from "./api";
import { type ReactNode } from "react";

export function swrFetcher<T>(path: string): Promise<T> {
  return fetchJson<T>(path);
}

export function SWRProvider({ children }: { children: ReactNode }) {
  return (
    <SWRConfig
      value={{
        fetcher: swrFetcher,
        revalidateOnFocus: true,
        dedupingInterval: 5000,
        errorRetryCount: 3,
        // Exponential backoff : 1s, 2s, 4s (plafonne a 8s via Math.min).
        errorRetryInterval: 1000,
        onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
          const status = (err as { status?: number } | null)?.status;
          if (status && status >= 400 && status < 500) return; // pas de retry sur 4xx client
          const delay = Math.min(1000 * 2 ** retryCount, 8000);
          setTimeout(() => revalidate({ retryCount }), delay);
        },
      }}
    >
      {children}
    </SWRConfig>
  );
}
