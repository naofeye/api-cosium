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
        revalidateOnFocus: false,
        dedupingInterval: 5000,
        errorRetryCount: 2,
      }}
    >
      {children}
    </SWRConfig>
  );
}
