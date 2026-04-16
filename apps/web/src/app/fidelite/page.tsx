"use client";

import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { KPICard } from "@/components/ui/KPICard";
import { useCosiumFidelityCards, useCosiumSponsorships } from "@/lib/hooks/use-api";
import { CreditCard, Users, Gift } from "lucide-react";

interface FidelityItem {
  id?: number | string;
  customer_cosium_id?: string;
  customer_name?: string;
  card_number?: string;
  points?: number;
  status?: string;
}

interface SponsorshipItem {
  id?: number | string;
  sponsor_name?: string;
  sponsored_name?: string;
  date?: string;
  reward?: string;
  status?: string;
}

export default function FidelitePage() {
  const cards = useCosiumFidelityCards({ pageSize: 50 });
  const sponsorships = useCosiumSponsorships({ pageSize: 50 });

  const cardsItems: FidelityItem[] = Array.isArray(cards.data?.items)
    ? cards.data.items
    : Array.isArray(cards.data)
      ? cards.data
      : [];
  const sponsorItems: SponsorshipItem[] = Array.isArray(sponsorships.data?.items)
    ? sponsorships.data.items
    : Array.isArray(sponsorships.data)
      ? sponsorships.data
      : [];

  const totalPoints = cardsItems.reduce((acc, c) => acc + (c.points ?? 0), 0);

  return (
    <PageLayout
      title="Fidelite & Parrainages"
      description="Cartes de fidelite et programme de parrainage Cosium"
      breadcrumb={[{ label: "Fidelite" }]}
    >
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
        <KPICard icon={CreditCard} label="Cartes actives" value={cardsItems.length} color="primary" />
        <KPICard icon={Gift} label="Points cumules" value={totalPoints.toLocaleString("fr-FR")} color="success" />
        <KPICard icon={Users} label="Parrainages" value={sponsorItems.length} color="info" />
      </div>

      <section className="mb-8">
        <h2 className="text-lg font-semibold text-text-primary mb-3">Cartes de fidelite</h2>
        {cards.isLoading ? (
          <LoadingState text="Chargement des cartes..." />
        ) : cards.error ? (
          <ErrorState message="Impossible de charger les cartes de fidelite." onRetry={() => cards.mutate()} />
        ) : cardsItems.length === 0 ? (
          <EmptyState title="Aucune carte" description="Aucune carte de fidelite synchronisee depuis Cosium." />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Client</th>
                  <th className="px-4 py-3 text-left font-semibold">Carte</th>
                  <th className="px-4 py-3 text-right font-semibold">Points</th>
                  <th className="px-4 py-3 text-left font-semibold">Statut</th>
                </tr>
              </thead>
              <tbody>
                {cardsItems.map((c, i) => (
                  <tr key={c.id ?? i} className="border-b border-border last:border-0">
                    <td className="px-4 py-3">{c.customer_name ?? "-"}</td>
                    <td className="px-4 py-3 font-mono text-xs">{c.card_number ?? "-"}</td>
                    <td className="px-4 py-3 text-right tabular-nums">{c.points ?? 0}</td>
                    <td className="px-4 py-3 text-text-secondary">{c.status ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-text-primary mb-3">Parrainages</h2>
        {sponsorships.isLoading ? (
          <LoadingState text="Chargement des parrainages..." />
        ) : sponsorships.error ? (
          <ErrorState message="Impossible de charger les parrainages." onRetry={() => sponsorships.mutate()} />
        ) : sponsorItems.length === 0 ? (
          <EmptyState title="Aucun parrainage" description="Aucun parrainage synchronise depuis Cosium." />
        ) : (
          <div className="rounded-xl border border-border bg-bg-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left font-semibold">Parrain</th>
                  <th className="px-4 py-3 text-left font-semibold">Filleul</th>
                  <th className="px-4 py-3 text-left font-semibold">Date</th>
                  <th className="px-4 py-3 text-left font-semibold">Recompense</th>
                  <th className="px-4 py-3 text-left font-semibold">Statut</th>
                </tr>
              </thead>
              <tbody>
                {sponsorItems.map((s, i) => (
                  <tr key={s.id ?? i} className="border-b border-border last:border-0">
                    <td className="px-4 py-3">{s.sponsor_name ?? "-"}</td>
                    <td className="px-4 py-3">{s.sponsored_name ?? "-"}</td>
                    <td className="px-4 py-3 text-text-secondary">{s.date ?? "-"}</td>
                    <td className="px-4 py-3">{s.reward ?? "-"}</td>
                    <td className="px-4 py-3 text-text-secondary">{s.status ?? "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageLayout>
  );
}
