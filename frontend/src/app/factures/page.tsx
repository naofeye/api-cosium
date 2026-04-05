"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SearchInput } from "@/components/ui/SearchInput";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { Button } from "@/components/ui/Button";
import { useFactures } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { formatMoney } from "@/lib/format";
import { Download, Receipt } from "lucide-react";
import type { Facture } from "@/lib/types";

export default function FacturesPage() {
  const router = useRouter();
  const { data: factures, error, isLoading, mutate } = useFactures();
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!factures) return [];
    if (!search.trim()) return factures;
    const q = search.toLowerCase();
    return factures.filter(
      (f) =>
        f.numero.toLowerCase().includes(q) ||
        (f.customer_name || "").toLowerCase().includes(q) ||
        f.status.toLowerCase().includes(q),
    );
  }, [search, factures]);

  const handleExportCsv = () => {
    if (!filtered.length) return;
    const headers = ["Numero", "Client", "Statut", "Montant TTC", "Date emission"];
    const rows = filtered.map((f) => [
      f.numero,
      f.customer_name || "-",
      f.status,
      formatMoney(f.montant_ttc),
      f.date_emission,
    ]);
    exportToCsv("factures.csv", headers, rows);
  };

  const columns: Column<Facture>[] = [
    { key: "numero", header: "Numero", render: (row) => <span className="font-mono font-medium">{row.numero}</span> },
    { key: "customer", header: "Client", render: (row) => row.customer_name || "-" },
    { key: "status", header: "Statut", render: (row) => <StatusBadge status={row.status} /> },
    { key: "montant_ttc", header: "Montant TTC", render: (row) => <MoneyDisplay amount={row.montant_ttc} bold /> },
    { key: "date", header: "Date emission", render: (row) => <DateDisplay date={row.date_emission} /> },
  ];

  return (
    <PageLayout
      title="Factures"
      description="Gestion des factures"
      breadcrumb={[{ label: "Factures" }]}
      actions={
        <Button variant="outline" onClick={handleExportCsv}>
          <Download className="h-4 w-4 mr-1" /> Exporter CSV
        </Button>
      }
    >
      <div className="mb-6">
        <SearchInput placeholder="Rechercher une facture..." onSearch={setSearch} />
      </div>

      <DataTable
        columns={columns}
        data={filtered}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/factures/${row.id}`)}
        emptyTitle="Aucune facture"
        emptyDescription="Aucune facture. Les factures sont generees a partir des devis signes."
        emptyIcon={Receipt}
      />
    </PageLayout>
  );
}
