"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Button } from "@/components/ui/Button";
import { useAllCosiumDocuments } from "@/lib/hooks/use-api";
import { API_BASE } from "@/lib/api";
import { Download, FileStack, FileText, HardDrive, Layers } from "lucide-react";
import type { AllDocumentItem } from "@/lib/types";

function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 o";
  if (bytes < 1024) return `${bytes} o`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} Ko`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`;
}

const DOC_TYPE_LABELS: Record<string, string> = {
  ordonnance: "Ordonnance",
  devis: "Devis",
  facture: "Facture",
  attestation: "Attestation",
  mutuelle: "Mutuelle",
  courrier: "Courrier",
  autre: "Autre",
};

const DOC_TYPE_STATUS: Record<string, string> = {
  ordonnance: "en_cours",
  devis: "brouillon",
  facture: "facturee",
  attestation: "complet",
  mutuelle: "soumise",
  courrier: "planifiee",
  autre: "archive",
};

export default function DocumentsCosiumPage() {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [docTypeFilter, setDocTypeFilter] = useState("");

  const { data, error, isLoading, mutate } = useAllCosiumDocuments({
    page,
    page_size: 25,
    search: search || undefined,
    doc_type: docTypeFilter || undefined,
  });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const handleClientClick = (item: AllDocumentItem) => {
    if (item.customer_id) {
      router.push(`/clients/${item.customer_id}`);
    }
  };

  const handleDownload = (item: AllDocumentItem) => {
    const url = `${API_BASE}/cosium-documents/local/${item.id}/download`;
    window.open(url, "_blank");
  };

  const docTypes = data?.type_counts ? Object.keys(data.type_counts).sort() : [];

  const columns: Column<AllDocumentItem>[] = [
    {
      key: "customer_name",
      header: "Client",
      sortable: true,
      render: (row) =>
        row.customer_id ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleClientClick(row);
            }}
            className="text-blue-600 hover:text-blue-700 hover:underline font-medium text-left text-sm"
            title="Voir la fiche client"
          >
            {row.customer_name || `Client #${row.customer_cosium_id}`}
          </button>
        ) : (
          <span className="text-sm text-gray-600">
            {row.customer_name || `Cosium #${row.customer_cosium_id}`}
          </span>
        ),
    },
    {
      key: "name",
      header: "Document",
      sortable: true,
      render: (row) => (
        <span className="text-sm font-medium text-gray-900 truncate max-w-xs block" title={row.name || ""}>
          {row.name || `Document #${row.cosium_document_id}`}
        </span>
      ),
    },
    {
      key: "document_type",
      header: "Type OCR",
      render: (row) =>
        row.document_type ? (
          <StatusBadge
            status={DOC_TYPE_STATUS[row.document_type] || "archive"}
            label={DOC_TYPE_LABELS[row.document_type] || row.document_type}
          />
        ) : (
          <span className="text-xs text-gray-400 italic">Non classifie</span>
        ),
    },
    {
      key: "classification_confidence",
      header: "Confiance",
      render: (row) => {
        if (row.classification_confidence === null || row.classification_confidence === undefined) {
          return <span className="text-xs text-gray-400">-</span>;
        }
        const pct = Math.round(row.classification_confidence * 100);
        const color =
          pct >= 80
            ? "text-emerald-600"
            : pct >= 50
              ? "text-amber-600"
              : "text-red-600";
        return <span className={`text-sm font-medium tabular-nums ${color}`}>{pct}%</span>;
      },
    },
    {
      key: "synced_at",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.synced_at ? (
          <DateDisplay date={row.synced_at} />
        ) : (
          <span className="text-text-secondary text-sm">-</span>
        ),
    },
    {
      key: "size_bytes",
      header: "Taille",
      sortable: true,
      className: "text-right",
      render: (row) => (
        <span className="text-sm text-gray-600 tabular-nums">{formatFileSize(row.size_bytes)}</span>
      ),
    },
    {
      key: "actions" as keyof AllDocumentItem,
      header: "",
      render: (row) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation();
            handleDownload(row);
          }}
          aria-label="Telecharger le document"
          title="Telecharger"
        >
          <Download className="h-4 w-4" />
        </Button>
      ),
    },
  ];

  return (
    <PageLayout
      title="Documents Cosium"
      description={`${data?.total ?? 0} documents telecharges depuis Cosium`}
      breadcrumb={[{ label: "Documents Cosium" }]}
    >
      {/* KPI bar */}
      {data && data.total > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-blue-50 p-2">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Total documents</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{data.total}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-emerald-50 p-2">
              <Layers className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Types identifies</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">{docTypes.length}</p>
            </div>
          </div>
          <div className="rounded-xl bg-white border border-gray-200 shadow-sm p-4 flex items-center gap-3">
            <div className="rounded-lg bg-amber-50 p-2">
              <HardDrive className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Taille totale</p>
              <p className="text-xl font-bold text-gray-900 tabular-nums">
                {formatFileSize(data.total_size_bytes)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Type counts breakdown */}
      {data && Object.keys(data.type_counts).length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {Object.entries(data.type_counts)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => (
              <button
                key={type}
                onClick={() => {
                  setDocTypeFilter(docTypeFilter === type ? "" : type);
                  setPage(1);
                }}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  docTypeFilter === type
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                }`}
              >
                {DOC_TYPE_LABELS[type] || type}
                <span className="tabular-nums">({count})</span>
              </button>
            ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <SearchInput placeholder="Rechercher par nom de document ou client..." onSearch={handleSearch} />
        <select
          value={docTypeFilter}
          onChange={(e) => {
            setDocTypeFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-border bg-bg-card px-3 py-2 text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary"
          aria-label="Filtrer par type de document"
        >
          <option value="">Tous les types</option>
          {docTypes.map((t) => (
            <option key={t} value={t}>
              {DOC_TYPE_LABELS[t] || t}
            </option>
          ))}
        </select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        page={page}
        pageSize={25}
        total={data?.total}
        onPageChange={setPage}
        emptyTitle="Aucun document Cosium"
        emptyDescription="Lancez une synchronisation des documents depuis Parametres > Connexion ERP pour telecharger vos documents."
        emptyIcon={FileStack}
      />
    </PageLayout>
  );
}
