"use client";

import { useCallback, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useToast } from "@/components/ui/Toast";
import { useClients } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { fetchJson, API_BASE } from "@/lib/api";
import Link from "next/link";
import { Download, Upload, AlertTriangle, Users, FileSpreadsheet } from "lucide-react";
import type { Customer } from "@/lib/types";
import { ImportDialog } from "./components/ImportDialog";
import { DuplicatesPanel, type DuplicateGroup } from "./components/DuplicatesPanel";

export default function ClientsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [dupesPending, startDupesTransition] = useTransition();
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [creatingSegment, setCreatingSegment] = useState(false);

  const { data, error, isLoading, mutate } = useClients({ q: search || undefined, page });

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const handleExportCsv = () => {
    const items = data?.items ?? [];
    if (items.length === 0) return;
    const headers = ["ID", "Nom", "Prenom", "Telephone", "Email", "Ville", "Date creation"];
    const rows = items.map((c) => [
      String(c.id), c.last_name, c.first_name, c.phone || "", c.email || "", c.city || "", c.created_at || "",
    ]);
    exportToCsv("clients.csv", headers, rows);
  };

  const handleExportComplet = () => {
    window.open(`${API_BASE}/exports/clients-complet`, "_blank");
  };

  const handleShowDuplicates = () => {
    if (showDuplicates) {
      setShowDuplicates(false);
      return;
    }
    startDupesTransition(async () => {
      try {
        const result = await fetchJson<DuplicateGroup[]>("/clients/duplicates");
        setDuplicates(result);
        setShowDuplicates(true);
      } catch (err) {
        toast(err instanceof Error ? err.message : "Erreur", "error");
      }
    });
  };

  const handleRefreshDuplicates = async () => {
    try {
      const updated = await fetchJson<DuplicateGroup[]>("/clients/duplicates");
      setDuplicates(updated);
    } catch {
      setShowDuplicates(false);
    }
  };

  const toggleSelectClient = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    const items = data?.items ?? [];
    if (selectedIds.size === items.length && items.length > 0) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((c) => c.id)));
    }
  };

  const handleExportSelection = () => {
    const items = data?.items ?? [];
    const selected = items.filter((c) => selectedIds.has(c.id));
    if (selected.length === 0) return;
    const headers = ["ID", "Nom", "Prenom", "Telephone", "Email", "Ville", "Date creation"];
    const rows = selected.map((c) => [
      String(c.id), c.last_name, c.first_name, c.phone || "", c.email || "", c.city || "", c.created_at || "",
    ]);
    exportToCsv(`clients_selection_${selected.length}.csv`, headers, rows);
    toast(`${selected.length} client(s) exporte(s) en CSV.`, "success");
  };

  const handleCreateSegment = async () => {
    if (selectedIds.size === 0) return;
    setCreatingSegment(true);
    try {
      const segmentName = `Selection manuelle du ${new Date().toLocaleDateString("fr-FR")}`;
      await fetchJson("/marketing/segments", {
        method: "POST",
        body: JSON.stringify({
          name: segmentName,
          criteria: { manual_ids: Array.from(selectedIds) },
        }),
      });
      toast(`Segment "${segmentName}" cree avec ${selectedIds.size} client(s).`, "success");
      setSelectedIds(new Set());
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la creation du segment", "error");
    } finally {
      setCreatingSegment(false);
    }
  };

  const columns: Column<Customer>[] = [
    {
      key: "select",
      header: (
        <input
          type="checkbox"
          checked={selectedIds.size > 0 && selectedIds.size === (data?.items ?? []).length}
          onChange={toggleSelectAll}
          aria-label="Tout selectionner"
        />
      ),
      render: (row) => (
        <input
          type="checkbox"
          checked={selectedIds.has(row.id)}
          onChange={(e) => { e.stopPropagation(); toggleSelectClient(row.id); }}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Selectionner ${row.first_name} ${row.last_name}`}
        />
      ),
    },
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    {
      key: "name",
      header: "Nom",
      render: (row) => (
        <div className="flex items-center gap-2">
          {row.avatar_url ? (
            <img src={`${API_BASE}/clients/${row.id}/avatar`} alt={`Photo de ${row.first_name} ${row.last_name}`} className="h-8 w-8 rounded-full object-cover" />
          ) : (
            <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-700">
              {(row.first_name?.[0] || "").toUpperCase()}
              {(row.last_name?.[0] || "").toUpperCase()}
            </div>
          )}
          <span className="font-medium">
            {row.last_name} {row.first_name}
          </span>
        </div>
      ),
    },
    { key: "phone", header: "Telephone", render: (row) => row.phone || "\u2014" },
    { key: "email", header: "Email", render: (row) => row.email || "\u2014" },
    { key: "city", header: "Ville", render: (row) => row.city || "\u2014" },
    {
      key: "completeness",
      header: "Completude",
      render: (row) => {
        const score = row.completeness?.score ?? 0;
        const colorClass =
          score >= 75 ? "bg-emerald-500" :
          score >= 50 ? "bg-amber-500" :
          score >= 25 ? "bg-orange-500" :
          "bg-red-500";
        const textColor =
          score >= 75 ? "text-emerald-700" :
          score >= 50 ? "text-amber-700" :
          score >= 25 ? "text-orange-700" :
          "text-red-700";
        return (
          <div className="flex items-center gap-2" title={`Completude : ${score}%`}>
            <div className="w-16 h-2 rounded-full bg-gray-200 overflow-hidden">
              <div
                className={`h-full rounded-full ${colorClass} transition-all`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className={`text-xs font-medium ${textColor}`}>{score}%</span>
          </div>
        );
      },
    },
    { key: "date", header: "Cree le", render: (row) => <DateDisplay date={row.created_at} /> },
  ];

  return (
    <PageLayout
      title="Clients"
      description="Gestion des clients"
      breadcrumb={[{ label: "Clients" }]}
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleShowDuplicates} disabled={dupesPending}>
            <AlertTriangle className="h-4 w-4 mr-1" />
            {dupesPending ? "Recherche..." : showDuplicates ? "Masquer doublons" : "Doublons"}
          </Button>
          <Button variant="outline" onClick={() => setShowImportDialog(true)}>
            <Upload className="h-4 w-4 mr-1" />
            Importer
          </Button>
          <Button variant="outline" onClick={handleExportCsv}>
            <Download className="h-4 w-4 mr-1" /> Exporter CSV
          </Button>
          <Button variant="outline" onClick={handleExportComplet}>
            <FileSpreadsheet className="h-4 w-4 mr-1" /> Exporter tout
          </Button>
          <Link href="/clients/new">
            <Button>Nouveau client</Button>
          </Link>
        </div>
      }
    >
      <ImportDialog
        open={showImportDialog}
        onClose={() => setShowImportDialog(false)}
        onImported={() => mutate()}
      />

      {showDuplicates && (
        <DuplicatesPanel
          duplicates={duplicates}
          onRefresh={handleRefreshDuplicates}
          onDataChanged={() => mutate()}
        />
      )}

      {data && data.items.length > 0 && (
        <div className="flex items-center gap-6 mb-4 text-sm text-text-secondary">
          <span>{data.total ?? data.items.length} client{(data.total ?? data.items.length) > 1 ? "s" : ""}</span>
          <span className="text-gray-300">|</span>
          <span>{data.items.filter((c) => c.email).length} avec email</span>
          <span className="text-gray-300">|</span>
          <span>{data.items.filter((c) => c.phone).length} avec telephone</span>
        </div>
      )}

      {/* Batch action bar */}
      {selectedIds.size > 0 && (
        <div className="mb-4 flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
          <span className="text-sm font-medium text-blue-800">
            {selectedIds.size} client{selectedIds.size > 1 ? "s" : ""} selectionne{selectedIds.size > 1 ? "s" : ""}
          </span>
          <div className="flex-1" />
          <Button variant="outline" onClick={handleExportSelection}>
            <Download className="h-4 w-4 mr-1" />
            Exporter la selection (CSV)
          </Button>
          <Button onClick={handleCreateSegment} disabled={creatingSegment}>
            <Users className="h-4 w-4 mr-1" />
            {creatingSegment ? "Creation..." : "Creer un segment marketing"}
          </Button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="text-sm text-blue-600 hover:text-blue-800 ml-2"
            aria-label="Tout deselectionner"
          >
            Tout deselectionner
          </button>
        </div>
      )}

      <div className="mb-6">
        <SearchInput placeholder="Rechercher un client (nom, email, telephone, ville)..." onSearch={handleSearch} />
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/clients/${row.id}`)}
        emptyTitle="Aucun client"
        emptyDescription="Importez vos clients depuis Cosium ou creez-en un manuellement."
        emptyIcon={Users}
        emptyAction={
          <div className="flex gap-2">
            <Link href="/admin">
              <Button variant="outline">Synchroniser Cosium</Button>
            </Link>
            <Link href="/clients/new">
              <Button>Creer un client</Button>
            </Link>
          </div>
        }
        page={page}
        pageSize={25}
        total={data?.total}
        onPageChange={setPage}
      />
    </PageLayout>
  );
}
