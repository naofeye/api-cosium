"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import useSWR from "swr";
import { User, Phone, Mail, Eye, Calendar, Euro } from "lucide-react";
import Link from "next/link";
import { formatMoney } from "@/lib/format";

interface ClientQuickData {
  id: number;
  first_name: string;
  last_name: string;
  phone: string | null;
  email: string | null;
  correction_od: string | null;
  correction_og: string | null;
  last_visit: string | null;
  ca_total: number;
}

interface ClientHoverCardProps {
  clientId: number;
  clientName?: string;
  children: React.ReactNode;
}

/**
 * Wrap any client name element with this component to show
 * a quick-view hover card after 300ms delay.
 * Uses SWR cache so no extra API calls if the data is already loaded.
 */
export function ClientHoverCard({ clientId, clientName, children }: ClientHoverCardProps) {
  const [isHovering, setIsHovering] = useState(false);
  const [showCard, setShowCard] = useState(false);
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Only fetch when card should be shown (SWR caches the result)
  const { data, isLoading } = useSWR<ClientQuickData>(
    showCard ? `/clients/${clientId}/quick` : null,
    { revalidateOnFocus: false, dedupingInterval: 60000 },
  );

  const handleMouseEnter = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
    setIsHovering(true);
    hoverTimerRef.current = setTimeout(() => {
      setShowCard(true);
    }, 300);
  }, []);

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current);
      hoverTimerRef.current = null;
    }
    setIsHovering(false);
    hideTimerRef.current = setTimeout(() => {
      setShowCard(false);
    }, 200);
  }, []);

  useEffect(() => {
    return () => {
      if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current);
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, []);

  const displayName = clientName || (data ? `${data.first_name} ${data.last_name}` : "Client");

  return (
    <div
      ref={containerRef}
      className="relative inline-block"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {children}

      {showCard && (
        <div
          className="absolute left-0 top-full mt-1 z-50 w-72 rounded-xl border border-border bg-bg-card shadow-xl"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          role="tooltip"
        >
          {isLoading || !data ? (
            <div className="p-4 space-y-2 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
              <div className="h-3 bg-gray-200 rounded w-2/3" />
            </div>
          ) : (
            <>
              {/* Header */}
              <div className="flex items-center gap-3 border-b border-border px-4 py-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <User className="h-4 w-4" aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-text-primary truncate">
                    {data.first_name} {data.last_name}
                  </p>
                  {data.email && (
                    <p className="text-xs text-text-secondary truncate">{data.email}</p>
                  )}
                </div>
              </div>

              {/* Info rows */}
              <div className="px-4 py-3 space-y-2">
                {data.phone && (
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Phone className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>{data.phone}</span>
                  </div>
                )}
                {data.email && (
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Mail className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span className="truncate">{data.email}</span>
                  </div>
                )}
                {(data.correction_od || data.correction_og) && (
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Eye className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>
                      OD: {data.correction_od || "-"} / OG: {data.correction_og || "-"}
                    </span>
                  </div>
                )}
                {data.last_visit && (
                  <div className="flex items-center gap-2 text-xs text-text-secondary">
                    <Calendar className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span>Derniere visite : {data.last_visit}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-xs">
                  <Euro className="h-3.5 w-3.5 shrink-0 text-text-secondary" aria-hidden="true" />
                  <span className="font-medium text-text-primary">
                    CA : {formatMoney(data.ca_total)}
                  </span>
                </div>
              </div>

              {/* Footer link */}
              <div className="border-t border-border px-4 py-2">
                <Link
                  href={`/clients/${clientId}`}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Voir le profil complet
                </Link>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
