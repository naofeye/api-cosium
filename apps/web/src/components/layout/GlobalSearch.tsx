"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Search, X, User, FolderOpen, FileText, Receipt, CreditCard, Stethoscope } from "lucide-react";
import { SEARCH_DEBOUNCE_MS, SEARCH_MIN_CHARS } from "@/lib/constants";

interface SearchResultItem {
  id: number;
  type: string;
  label: string;
  detail: string;
  /** Extended context fields for richer previews */
  phone?: string | null;
  city?: string | null;
  last_visit_date?: string | null;
  amount?: number | null;
  client_name?: string | null;
  date?: string | null;
  prescriber_name?: string | null;
  correction_summary?: string | null;
  document_type?: string | null;
}

interface SearchResults {
  clients: SearchResultItem[];
  dossiers: SearchResultItem[];
  devis: SearchResultItem[];
  factures: SearchResultItem[];
  cosium_factures: SearchResultItem[];
  ordonnances: SearchResultItem[];
}

function formatSearchDate(date: string | null | undefined): string {
  if (!date) return "";
  try {
    return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(date));
  } catch {
    return date;
  }
}

function formatSearchMoney(amount: number | null | undefined): string {
  if (amount === null || amount === undefined) return "";
  return new Intl.NumberFormat("fr-FR", { style: "currency", currency: "EUR", minimumFractionDigits: 2 }).format(amount);
}

/** Build rich context chips for a search result based on type */
function buildContextParts(item: SearchResultItem): string[] {
  const parts: string[] = [];
  switch (item.type) {
    case "client":
      if (item.phone) parts.push(item.phone);
      if (item.city) parts.push(item.city);
      if (item.last_visit_date) parts.push(`Visite : ${formatSearchDate(item.last_visit_date)}`);
      break;
    case "facture":
    case "cosium_facture":
      if (item.amount !== null && item.amount !== undefined) parts.push(formatSearchMoney(item.amount));
      if (item.client_name) parts.push(item.client_name);
      if (item.date) parts.push(formatSearchDate(item.date));
      break;
    case "ordonnance":
      if (item.date) parts.push(formatSearchDate(item.date));
      if (item.prescriber_name) parts.push(item.prescriber_name);
      if (item.correction_summary) parts.push(item.correction_summary);
      break;
    case "devis":
      if (item.amount !== null && item.amount !== undefined) parts.push(formatSearchMoney(item.amount));
      if (item.client_name) parts.push(item.client_name);
      break;
    case "dossier":
      if (item.client_name) parts.push(item.client_name);
      if (item.date) parts.push(formatSearchDate(item.date));
      break;
  }
  return parts;
}

const TYPE_CONFIG = {
  client: { icon: User, href: (id: number) => `/clients/${id}`, color: "text-blue-600", label: "Client" },
  dossier: { icon: FolderOpen, href: (id: number) => `/cases/${id}`, color: "text-amber-600", label: "Dossier" },
  devis: { icon: FileText, href: (id: number) => `/devis/${id}`, color: "text-purple-600", label: "Devis" },
  facture: { icon: Receipt, href: (id: number) => `/factures/${id}`, color: "text-emerald-600", label: "Facture" },
  cosium_facture: { icon: CreditCard, href: () => `/cosium-factures`, color: "text-teal-600", label: "Facture Cosium" },
  ordonnance: { icon: Stethoscope, href: (id: number) => `/ordonnances/${id}`, color: "text-rose-600", label: "Ordonnance" },
} as const;

export function GlobalSearch() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // Debounce
  useEffect(() => {
    clearTimeout(timeoutRef.current);
    timeoutRef.current = setTimeout(() => setDebouncedQuery(query), SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timeoutRef.current);
  }, [query]);

  // SWR avec cle conditionnelle
  const { data } = useSWR<SearchResults>(
    debouncedQuery.length >= SEARCH_MIN_CHARS ? `/search?q=${encodeURIComponent(debouncedQuery)}` : null,
  );

  // Fermer au clic exterieur
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Fermer avec Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const allResults = data
    ? [
        ...data.clients.map((r) => ({ ...r, type: "client" as const })),
        ...data.dossiers.map((r) => ({ ...r, type: "dossier" as const })),
        ...data.devis.map((r) => ({ ...r, type: "devis" as const })),
        ...data.factures.map((r) => ({ ...r, type: "facture" as const })),
        ...(data.cosium_factures || []).map((r) => ({ ...r, type: "cosium_facture" as const })),
        ...(data.ordonnances || []).map((r) => ({ ...r, type: "ordonnance" as const })),
      ]
    : [];

  const handleSelect = (item: SearchResultItem & { type: keyof typeof TYPE_CONFIG }) => {
    setOpen(false);
    setQuery("");
    router.push(TYPE_CONFIG[item.type].href(item.id));
  };

  const showDropdown = open && debouncedQuery.length >= SEARCH_MIN_CHARS;

  return (
    <div ref={containerRef} className="relative w-full max-w-md">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" aria-hidden="true" />
        <input
          type="search"
          role="combobox"
          aria-expanded={showDropdown}
          aria-haspopup="listbox"
          aria-controls="global-search-results"
          aria-label="Recherche globale"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          placeholder="Rechercher un client, dossier, devis, facture..."
          className="w-full rounded-lg border border-border bg-gray-50 dark:bg-gray-800 py-2 pl-10 pr-8 text-sm outline-none focus:border-primary focus:bg-white dark:focus:bg-gray-900 focus:ring-1 focus:ring-primary"
        />
        {/* Ctrl+K hint */}
        {!query && (
          <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline text-xs text-text-secondary bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded font-mono">
            Ctrl+K
          </span>
        )}
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setOpen(false);
            }}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label="Effacer"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {showDropdown && (
        <div id="global-search-results" role="listbox" aria-label="Resultats de recherche" className="absolute top-full left-0 right-0 mt-1 max-h-80 overflow-y-auto rounded-xl border border-border bg-bg-card shadow-xl z-50">
          {allResults.length === 0 && (
            <div className="px-4 py-6 text-center text-sm text-text-secondary">
              Aucun resultat pour &quot;{debouncedQuery}&quot;
            </div>
          )}
          {allResults.length > 0 && (
            <ul className="py-1">
              {allResults.map((item, i) => {
                const config = TYPE_CONFIG[item.type as keyof typeof TYPE_CONFIG];
                const Icon = config.icon;
                return (
                  <li key={`${item.type}-${item.id}-${i}`} role="option" aria-selected={false}>
                    <button
                      onClick={() => handleSelect(item as SearchResultItem & { type: keyof typeof TYPE_CONFIG })}
                      className="flex w-full items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none"
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${config.color}`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-text-primary truncate">{item.label}</p>
                        {item.detail && <p className="text-xs text-text-secondary truncate">{item.detail}</p>}
                        {(() => {
                          const ctx = buildContextParts(item);
                          if (ctx.length === 0) return null;
                          return (
                            <p className="text-xs text-text-secondary truncate mt-0.5">
                              {ctx.join(" \u00b7 ")}
                            </p>
                          );
                        })()}
                      </div>
                      <span className="text-xs text-text-secondary whitespace-nowrap">{config.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
