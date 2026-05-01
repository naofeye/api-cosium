"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { KPICard } from "@/components/ui/KPICard";
import { useDevisList } from "@/lib/hooks/use-api";
import { formatMoney, formatPercent } from "@/lib/format";
import Link from "next/link";
import { FileText, TrendingUp, ShoppingCart, PenLine, CheckCircle } from "lucide-react";
import type { Devis } from "@/lib/types";

type StatusTab = "tous" | "brouillon" | "envoye" | "signe" | "facture" | "refuse" | "annule";

const STATUS_TABS: { key: StatusTab; label: string }[] = [
  { key: "tous", label: "Tous" },
  { key: "brouillon", label: "Brouillons" },
  { key: "envoye", label: "Envoyes" },
  { key: "signe", label: "Signes" },
  { key: "facture", label: "Factures" },
  { key: "refuse", label: "Refuses" },
  { key: "annule", label: "Annules" },
];

export default function DevisListPage() {
  const router = useRouter();
  const { data: devisList, error, isLoading, mutate } = useDevisList();
  const [search, setSearch] = useState("");
  const [activeTab, setActiveTab] = useState<StatusTab>("tous");

  /* ─── KPIs ─── */
  const kpis = useMemo(() => {
    if (!devisList) return { enCours: 0, signeMois: 0, tauxConversion: 0, panierMoyen: 0 };

    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);

    const enCours = devisList.filter((d) => d.status === "envoye" || d.status === "brouillon").length;
    const signes = devisList.filter((d) => d.status === "signe" || d.status === "facture");
    const signeMois = signes.filter((d) => new Date(d.created_at) >= startOfMonth).length;

    const totalNonDraft = devisList.filter((d) => d.status !== "brouillon").length;
    const totalConverted = devisList.filter((d) => d.status === "signe" || d.status === "facture").length;
    const tauxConversion = totalNonDraft > 0 ? Math.round((totalConverted / totalNonDraft) * 100) : 0;

    const allTtc = devisList.map((d) => d.montant_ttc);
    const panierMoyen = allTtc.length > 0 ? allTtc.reduce((a, b) => a + b, 0) / allTtc.length : 0;

    return { enCours, signeMois, tauxConversion, panierMoyen };
  }, [devisList]);

  /* ─── Tab counts ─── */
  const tabCounts = useMemo(() => {
    if (!devisList) return {} as Record<StatusTab, number>;
    const counts: Record<string, number> = { tous: devisList.length };
    for (const d of devisList) {
      counts[d.status] = (counts[d.status] || 0) + 1;
    }
    return counts;
  }, [devisList]);

  /* ─── Filtered data ─── */
  const filtered = useMemo(() => {
    if (!devisList) return [];
    let result = devisList;
    if (activeTab !== "tous") {
      result = result.filter((d) => d.status === activeTab);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((d) => d.numero.toLowerCase().includes(q) || d.status.toLowerCase().includes(q));
    }
    return result;
  }, [search, activeTab, devisList]);

  const columns: Column<Devis>[] = [
    { key: "numero", header: "Numero", render: (row) => <span className="font-mono font-medium">{row.numero}</span> },
    { key: "customer", header: "Dossier", render: (row) => `Dossier #${row.case_id}` },
    { key: "status", header: "Statut", render: (row) => <StatusBadge status={row.status} /> },
    { key: "montant_ttc", header: "Montant TTC", render: (row) => <MoneyDisplay amount={row.montant_ttc} bold /> },
    {
      key: "reste",
      header: "Reste a charge",
      render: (row) => <MoneyDisplay amount={row.reste_a_charge} colored />,
    },
    { key: "date", header: "Date", render: (row) => <DateDisplay date={row.created_at} /> },
    {
      key: "valid_until",
      header: "Valide jusqu'au",
      render: (row) => {
        if (!row.valid_until) return <span className="text-text-secondary">—</span>;
        const exp = new Date(row.valid_until);
        const now = new Date();
        const days = Math.ceil((exp.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
        const isExpired = row.status === "expire" || days < 0;
        const isWarning = !isExpired && days <= 7;
        return (
          <span
            className={
              isExpired
                ? "font-medium text-red-600"
                : isWarning
                ? "font-medium text-amber-600"
                : "text-text-secondary"
            }
          >
            <DateDisplay date={row.valid_until} />
            {isWarning && <span className="ml-1 text-xs">(J-{days})</span>}
          </span>
        );
      },
    },
  ];

  return (
    <PageLayout
      title="Devis"
      description="Gestion des devis clients"
      breadcrumb={[{ label: "Devis" }]}
      actions={
        <Link href="/devis/new">
          <Button>Nouveau devis</Button>
        </Link>
      }
    >
      {/* KPI Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KPICard icon={PenLine} label="Devis en cours" value={kpis.enCours} color="info" />
        <KPICard icon={CheckCircle} label="Signes ce mois" value={kpis.signeMois} color="success" />
        <KPICard
          icon={TrendingUp}
          label="Taux de conversion"
          value={`${kpis.tauxConversion}%`}
          color={kpis.tauxConversion >= 50 ? "success" : "warning"}
        />
        <KPICard icon={ShoppingCart} label="Panier moyen" value={formatMoney(kpis.panierMoyen)} color="primary" />
      </div>

      {/* Status filter tabs */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-0 overflow-x-auto" role="tablist" aria-label="Filtrer par statut">
          {STATUS_TABS.map((tab) => {
            const count = tabCounts[tab.key] ?? 0;
            return (
              <button
                key={tab.key}
                role="tab"
                aria-selected={activeTab === tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${
                  activeTab === tab.key
                    ? "border-primary text-primary"
                    : "border-transparent text-text-secondary hover:text-text-primary"
                }`}
              >
                {tab.label}
                {count > 0 && (
                  <span
                    className={`ml-1.5 inline-flex items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-semibold leading-none ${
                      activeTab === tab.key ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    {count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <SearchInput placeholder="Rechercher un devis..." onSearch={setSearch} />
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/devis/${row.id}`)}
        getRowHref={(row) => `/devis/${row.id}`}
        emptyTitle="Aucun devis"
        emptyDescription={
          activeTab !== "tous"
            ? `Aucun devis avec le statut "${activeTab.replace(/_/g, " ")}".`
            : "Creez votre premier devis pour un client."
        }
        emptyIcon={FileText}
        emptyAction={
          activeTab === "tous" ? (
            <Link href="/devis/new">
              <Button>Creer un devis</Button>
            </Link>
          ) : undefined
        }
      />
    </PageLayout>
  );
}
