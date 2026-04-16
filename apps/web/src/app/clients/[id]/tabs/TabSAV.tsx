"use client";

import useSWR from "swr";
import { EmptyState } from "@/components/ui/EmptyState";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { SAVTracker } from "@/components/ui/SAVTracker";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Briefcase } from "lucide-react";

interface SAVItem {
  cosium_id?: number | string;
  id?: number | string;
  reference?: string;
  status?: string;
  subject?: string;
  creation_date?: string | null;
  return_date?: string | null;
  site?: string;
  repairer?: string;
}

interface TabSAVProps {
  cosiumId: string | number | null;
}

function buildSteps(status?: string): { label: string; status: "done" | "current" | "pending"; date?: string }[] {
  const canonical = [
    "Reception",
    "Diagnostic",
    "Reparation",
    "Controle qualite",
    "Retour client",
  ];
  const s = (status ?? "").toLowerCase();
  let currentIdx = 0;
  if (/diagn/.test(s)) currentIdx = 1;
  else if (/repar/.test(s)) currentIdx = 2;
  else if (/contr|qualit/.test(s)) currentIdx = 3;
  else if (/retour|livr|termin|clos|ferm/.test(s)) currentIdx = 4;
  return canonical.map((label, i) => ({
    label,
    status: i < currentIdx ? "done" : i === currentIdx ? "current" : "pending",
  }));
}

export function TabSAV({ cosiumId }: TabSAVProps) {
  const { data, error, isLoading, mutate } = useSWR<SAVItem[]>(
    cosiumId ? `/cosium/sav?customer_cosium_id=${cosiumId}` : null,
    { shouldRetryOnError: false },
  );

  if (!cosiumId) {
    return (
      <EmptyState
        title="Pas de client Cosium"
        description="Ce client n'est pas encore lie a Cosium, les dossiers SAV ne peuvent pas etre affiches."
      />
    );
  }
  if (isLoading) return <LoadingState text="Chargement des dossiers SAV..." />;
  if (error) return <ErrorState message="Impossible de charger les dossiers SAV." onRetry={() => mutate()} />;

  const items = Array.isArray(data) ? data : [];
  if (items.length === 0) {
    return (
      <EmptyState
        title="Aucun dossier SAV"
        description="Aucun dossier apres-vente trouve pour ce client."
      />
    );
  }

  return (
    <div className="space-y-4">
      {items.map((sav, i) => (
        <div
          key={sav.cosium_id ?? sav.id ?? i}
          className="rounded-xl border border-border bg-bg-card p-5 shadow-sm"
        >
          <div className="flex items-start justify-between gap-3 mb-4">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-100">
                <Briefcase className="h-4 w-4 text-amber-700" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold">
                  {sav.subject ?? sav.reference ?? `Dossier SAV #${sav.cosium_id ?? sav.id}`}
                </p>
                <p className="text-xs text-text-secondary mt-0.5">
                  {sav.creation_date ? <><span>Ouvert le </span><DateDisplay date={sav.creation_date} /></> : "Date inconnue"}
                  {sav.site && <span className="ml-2">· {sav.site}</span>}
                </p>
              </div>
            </div>
            {sav.status && (
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-700">
                {sav.status}
              </span>
            )}
          </div>
          <SAVTracker steps={buildSteps(sav.status)} />
        </div>
      ))}
    </div>
  );
}
