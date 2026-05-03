"use client";

import useSWR from "swr";
import Link from "next/link";
import { ChevronRight, KeyRound } from "lucide-react";

import { fetchJson } from "@/lib/api";

interface ApiToken {
  id: number;
  name: string;
  prefix: string;
  scopes: string[];
  revoked: boolean;
  last_used_at: string | null;
  created_at: string;
}

const fetcher = <T,>(url: string) => fetchJson<T>(url);

function isRecent(iso: string | null, hoursWindow: number): boolean {
  if (!iso) return false;
  const diffMs = Date.now() - new Date(iso).getTime();
  return diffMs < hoursWindow * 3600 * 1000;
}

/**
 * Widget pulse API publique : count tokens actifs, requetes 24h
 * (proxy via last_used_at), top 3 tokens recents.
 */
export function ApiPubliqueWidget() {
  const { data: tokens, isLoading, error } = useSWR<ApiToken[]>(
    "/admin/api-tokens",
    fetcher,
  );

  if (isLoading || error || !tokens) return null;
  if (tokens.length === 0) return null;

  const active = tokens.filter((t) => !t.revoked);
  const used24h = active.filter((t) => isRecent(t.last_used_at, 24));
  const top3 = [...used24h]
    .sort((a, b) => {
      const aT = a.last_used_at ? new Date(a.last_used_at).getTime() : 0;
      const bT = b.last_used_at ? new Date(b.last_used_at).getTime() : 0;
      return bT - aT;
    })
    .slice(0, 3);

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-semibold text-text-primary flex items-center gap-2">
          <KeyRound className="h-4 w-4" aria-hidden="true" />
          API publique v1
        </h3>
        <Link
          href="/admin/api-publique"
          className="text-xs text-blue-600 hover:underline flex items-center gap-1"
        >
          Gerer
          <ChevronRight size={12} aria-hidden="true" />
        </Link>
      </div>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <div>
          <p className="text-xs text-gray-500 uppercase font-semibold">Actifs</p>
          <p className="text-2xl font-bold tabular-nums text-gray-900">
            {active.length}
          </p>
          <p className="text-xs text-gray-500">
            sur {tokens.length} crees
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase font-semibold">
            Utilises 24h
          </p>
          <p className="text-2xl font-bold tabular-nums text-blue-600">
            {used24h.length}
          </p>
          <p className="text-xs text-gray-500">
            integrations actives
          </p>
        </div>
      </div>

      {top3.length > 0 ? (
        <div>
          <p className="text-xs text-gray-500 uppercase font-semibold mb-2">
            Top tokens recents
          </p>
          <ul className="space-y-1">
            {top3.map((t) => (
              <li
                key={t.id}
                className="flex justify-between items-center text-xs"
              >
                <span className="font-medium truncate max-w-[60%]">
                  {t.name}
                </span>
                <span className="text-gray-500 tabular-nums">
                  {t.last_used_at
                    ? new Date(t.last_used_at).toLocaleTimeString("fr-FR", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })
                    : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-xs text-gray-400 italic">
          Aucune utilisation dans les dernieres 24h.
        </p>
      )}
    </div>
  );
}
