"use client";

import { useState, useEffect } from "react";
import {
  X,
  Plus,
  CheckCircle2,
  Pencil,
  RefreshCw,
  Send,
  Paperclip,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";

interface AuditEntry {
  id: number;
  preparation_id: number;
  action: string;
  field_name: string | null;
  old_value: unknown;
  new_value: unknown;
  source: string | null;
  user_id: number;
  created_at: string | null;
}

const ACTION_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; icon: typeof Plus }
> = {
  created: {
    label: "Creation",
    color: "text-blue-700",
    bg: "bg-blue-100",
    icon: Plus,
  },
  field_validated: {
    label: "Champ valide",
    color: "text-emerald-700",
    bg: "bg-emerald-100",
    icon: CheckCircle2,
  },
  field_corrected: {
    label: "Champ corrige",
    color: "text-amber-700",
    bg: "bg-amber-100",
    icon: Pencil,
  },
  refreshed: {
    label: "Rafraichissement",
    color: "text-blue-700",
    bg: "bg-blue-100",
    icon: RefreshCw,
  },
  submitted: {
    label: "Soumission PEC",
    color: "text-emerald-700",
    bg: "bg-emerald-100",
    icon: Send,
  },
  document_attached: {
    label: "Document attache",
    color: "text-purple-700",
    bg: "bg-purple-100",
    icon: Paperclip,
  },
};

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    const d = new Date(iso);
    return d.toLocaleString("fr-FR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "-";
  if (typeof val === "object") {
    try {
      return JSON.stringify(val);
    } catch {
      return String(val);
    }
  }
  return String(val);
}

interface AuditTrailModalProps {
  preparationId: string;
  open: boolean;
  onClose: () => void;
}

export function AuditTrailModal({ preparationId, open, onClose }: AuditTrailModalProps) {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchJson<AuditEntry[]>(`/pec-preparations/${preparationId}/audit`)
      .then((result) => {
        if (!cancelled) setEntries(result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Erreur de chargement");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [preparationId, open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-gray-500" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-gray-900">Journal d&apos;audit</h2>
            <span className="text-xs text-gray-500">Preparation #{preparationId}</span>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Fermer">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading && (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="animate-pulse flex gap-3">
                  <div className="w-8 h-8 bg-gray-200 rounded-full shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-48" />
                    <div className="h-3 bg-gray-100 rounded w-32" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}

          {!loading && !error && entries.length === 0 && (
            <div className="text-center py-8">
              <Clock className="h-10 w-10 text-gray-300 mx-auto mb-3" aria-hidden="true" />
              <p className="text-sm text-gray-500">Aucune action enregistree pour le moment.</p>
            </div>
          )}

          {!loading && !error && entries.length > 0 && (
            <div className="relative">
              {/* Timeline line */}
              <div className="absolute left-4 top-2 bottom-2 w-0.5 bg-gray-200" aria-hidden="true" />

              <div className="space-y-4">
                {entries.map((entry) => {
                  const config = ACTION_CONFIG[entry.action] ?? {
                    label: entry.action,
                    color: "text-gray-700",
                    bg: "bg-gray-100",
                    icon: Clock,
                  };
                  const Icon = config.icon;

                  return (
                    <div key={entry.id} className="relative flex gap-3 pl-1">
                      {/* Icon */}
                      <div
                        className={cn(
                          "w-8 h-8 rounded-full flex items-center justify-center shrink-0 z-10",
                          config.bg,
                        )}
                      >
                        <Icon className={cn("h-4 w-4", config.color)} aria-hidden="true" />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0 pt-0.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={cn("text-sm font-medium", config.color)}>
                            {config.label}
                          </span>
                          {entry.field_name && (
                            <span className="text-xs text-gray-500 bg-gray-100 rounded px-1.5 py-0.5">
                              {entry.field_name}
                            </span>
                          )}
                          <span className="text-xs text-gray-400 ml-auto shrink-0">
                            {formatDate(entry.created_at)}
                          </span>
                        </div>

                        {/* Old -> New value for corrections */}
                        {entry.action === "field_corrected" && (
                          <div className="mt-1 text-xs flex items-center gap-1.5">
                            <span className="text-gray-400 line-through">
                              {formatValue(entry.old_value)}
                            </span>
                            <span className="text-gray-400" aria-hidden="true">&rarr;</span>
                            <span className="text-gray-900 font-medium">
                              {formatValue(entry.new_value)}
                            </span>
                          </div>
                        )}

                        {/* New value for creation/submission */}
                        {(entry.action === "created" || entry.action === "submitted") &&
                          entry.new_value != null && (
                            <p className="mt-1 text-xs text-gray-500">
                              {formatValue(entry.new_value)}
                            </p>
                          )}

                        {/* User */}
                        <p className="mt-0.5 text-xs text-gray-400">
                          Utilisateur #{entry.user_id}
                          {entry.source && ` — source: ${entry.source}`}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-gray-200 flex justify-end">
          <Button variant="outline" size="sm" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    </div>
  );
}
