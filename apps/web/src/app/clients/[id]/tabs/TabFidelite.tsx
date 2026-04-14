"use client";

import useSWR from "swr";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { Award, Gift, MessageSquare, AlertTriangle } from "lucide-react";
import { formatMoney } from "@/lib/format";

interface FidelityCard {
  cosium_id: number | null;
  card_number: string | null;
  amount: number | null;
  remaining_amount: number | null;
  remaining_consumable_amount: number | null;
  creation_date: string | null;
  expiration_date: string | null;
}

interface Sponsorship {
  cosium_id: number | null;
  sponsored_first_name: string | null;
  sponsored_last_name: string | null;
  amount: number | null;
  remaining_amount: number | null;
  creation_date: string | null;
  consumed: boolean;
}

interface Note {
  cosium_id: number | null;
  message: string;
  creation_date: string | null;
  author: string | null;
  appearance_label: string | null;
  status_label: string | null;
}

interface CosiumLiveData {
  customer_id: number;
  cosium_id: number | null;
  fidelity_cards: FidelityCard[];
  sponsorships: Sponsorship[];
  notes: Note[];
  errors: string[];
}

interface Props {
  clientId: string | number;
}

function frenchDate(iso: string | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleDateString("fr-FR");
  } catch {
    return iso.slice(0, 10);
  }
}

export function TabFidelite({ clientId }: Props) {
  const { data, error, isLoading, mutate } = useSWR<CosiumLiveData>(
    `/clients/${clientId}/cosium-live`,
    { refreshInterval: 0, shouldRetryOnError: false },
  );

  if (isLoading) return <LoadingState text="Chargement des donnees Cosium en direct..." />;
  if (error) return <ErrorState message="Impossible de charger les donnees fidelite" onRetry={() => mutate()} />;
  if (!data) return null;

  if (!data.cosium_id) {
    return (
      <EmptyState
        title="Client non lie a Cosium"
        description="Ce client n'a pas d'identifiant Cosium. La carte de fidelite, les parrainages et les notes CRM seront disponibles une fois la liaison effectuee."
      />
    );
  }

  const isEmpty = data.fidelity_cards.length === 0 && data.sponsorships.length === 0 && data.notes.length === 0;

  return (
    <div className="space-y-6">
      {data.errors.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-900">Donnees partiellement disponibles</p>
              <ul className="mt-1 text-xs text-amber-700 space-y-0.5">
                {data.errors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Cartes de fidelite */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Award className="h-5 w-5 text-emerald-600" />
          <h3 className="text-base font-semibold text-text-primary">Cartes de fidelite</h3>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">{data.fidelity_cards.length}</span>
        </div>
        {data.fidelity_cards.length === 0 ? (
          <p className="text-sm text-text-secondary italic">Aucune carte de fidelite</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.fidelity_cards.map((c) => (
              <div key={c.cosium_id ?? c.card_number} className="rounded-xl border border-border bg-bg-card p-4 shadow-sm">
                <div className="flex justify-between items-start mb-2">
                  <span className="text-xs font-mono text-text-secondary">N° {c.card_number ?? "?"}</span>
                  <span className="text-xs text-text-secondary">Cree {frenchDate(c.creation_date)}</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="block text-xs text-text-secondary">Montant initial</span>
                    <span className="font-semibold tabular-nums">{formatMoney(c.amount ?? 0)}</span>
                  </div>
                  <div>
                    <span className="block text-xs text-text-secondary">Restant</span>
                    <span className="font-semibold text-emerald-700 tabular-nums">{formatMoney(c.remaining_amount ?? 0)}</span>
                  </div>
                </div>
                {c.expiration_date && (
                  <p className="mt-2 text-xs text-amber-700">Expire le {frenchDate(c.expiration_date)}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Parrainages */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <Gift className="h-5 w-5 text-purple-600" />
          <h3 className="text-base font-semibold text-text-primary">Parrainages</h3>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">{data.sponsorships.length}</span>
        </div>
        {data.sponsorships.length === 0 ? (
          <p className="text-sm text-text-secondary italic">Aucun parrainage</p>
        ) : (
          <div className="space-y-2">
            {data.sponsorships.map((s) => (
              <div key={s.cosium_id} className="flex items-center justify-between rounded-lg border border-border bg-bg-card p-3">
                <div>
                  <p className="text-sm font-medium">
                    {s.sponsored_first_name} {s.sponsored_last_name}
                  </p>
                  <p className="text-xs text-text-secondary">{frenchDate(s.creation_date)}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold tabular-nums">{formatMoney(s.amount ?? 0)}</p>
                  <p className={`text-xs ${s.consumed ? "text-text-secondary" : "text-emerald-700"}`}>
                    {s.consumed ? "Consomme" : `Restant ${formatMoney(s.remaining_amount ?? 0)}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Notes CRM Cosium */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-blue-600" />
          <h3 className="text-base font-semibold text-text-primary">Notes CRM Cosium</h3>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">{data.notes.length}</span>
        </div>
        {data.notes.length === 0 ? (
          <p className="text-sm text-text-secondary italic">Aucune note CRM</p>
        ) : (
          <div className="space-y-2">
            {data.notes.map((n) => (
              <div key={n.cosium_id} className="rounded-lg border border-border bg-bg-card p-3">
                <p className="text-sm text-text-primary">{n.message}</p>
                <div className="mt-2 flex items-center gap-3 text-xs text-text-secondary">
                  <span>{frenchDate(n.creation_date)}</span>
                  {n.author && <span>par {n.author}</span>}
                  {n.appearance_label && <span className="rounded bg-gray-100 px-1.5 py-0.5">{n.appearance_label}</span>}
                  {n.status_label && <span className="rounded bg-blue-50 text-blue-700 px-1.5 py-0.5">{n.status_label}</span>}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {isEmpty && data.errors.length === 0 && (
        <EmptyState
          title="Aucune donnee de fidelisation"
          description="Ce client n'a ni carte de fidelite, ni parrainage, ni note CRM dans Cosium."
        />
      )}
    </div>
  );
}
