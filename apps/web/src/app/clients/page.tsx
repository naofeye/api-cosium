"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Download, FileSpreadsheet, Upload, Users } from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { useClients } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { fetchJson, API_BASE } from "@/lib/api";

import { ImportDialog } from "./components/ImportDialog";
import { DuplicatesPanel } from "./components/DuplicatesPanel";
import { BatchActionBar } from "./components/BatchActionBar";
import { buildClientsColumns } from "./components/clientsColumns";
import { useClientsSelection } from "./hooks/useClientsSelection";
import { useClientsDuplicates } from "./hooks/useClientsDuplicates";

const CSV_HEADERS = ["ID", "Nom", "Prenom", "Telephone", "Email", "Ville", "Date creation"];

function clientToRow(c: { id: number; last_name: string; first_name: string; phone?: string | null; email?: string | null; city?: string | null; created_at?: string | null }) {
  return [String(c.id), c.last_name, c.first_name, c.phone || "", c.email || "", c.city || "", c.created_at || ""];
}

export default function ClientsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [creatingSegment, setCreatingSegment] = useState(false);

  const { data, error, isLoading, mutate } = useClients({ q: search || undefined, page });

  const items = data?.items ?? [];
  const allIds = useMemo(() => items.map((c) => c.id), [items]);
  const { selectedIds, toggleOne, toggleAll, clear } = useClientsSelection(allIds);
  const dupes = useClientsDuplicates((msg) => toast(msg, "error"));

  const handleSearch = useCallback((q: string) => {
    setSearch(q);
    setPage(1);
  }, []);

  const handleExportCsv = () => {
    if (items.length === 0) return;
    exportToCsv("clients.csv", CSV_HEADERS, items.map(clientToRow));
  };

  const handleExportComplet = () => {
    window.open(`${API_BASE}/exports/clients-complet`, "_blank");
  };

  const handleExportSelection = () => {
    const selected = items.filter((c) => selectedIds.has(c.id));
    if (selected.length === 0) return;
    exportToCsv(`clients_selection_${selected.length}.csv`, CSV_HEADERS, selected.map(clientToRow));
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
      clear();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la creation du segment", "error");
    } finally {
      setCreatingSegment(false);
    }
  };

  const columns = useMemo(
    () => buildClientsColumns({ selectedIds, totalSelectable: items.length, onToggleOne: toggleOne, onToggleAll: toggleAll }),
    [selectedIds, items.length, toggleOne, toggleAll],
  );

  return (
    <PageLayout
      title="Clients"
      description="Gestion des clients"
      breadcrumb={[{ label: "Clients" }]}
      actions={
        <div className="flex gap-2">
          <Button variant="outline" onClick={dupes.toggle} disabled={dupes.pending}>
            <AlertTriangle className="h-4 w-4 mr-1" />
            {dupes.pending ? "Recherche..." : dupes.show ? "Masquer doublons" : "Doublons"}
          </Button>
          <Button variant="outline" onClick={() => setShowImportDialog(true)}>
            <Upload className="h-4 w-4 mr-1" /> Importer
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

      {dupes.show && (
        <DuplicatesPanel
          duplicates={dupes.duplicates}
          onRefresh={dupes.refresh}
          onDataChanged={() => mutate()}
        />
      )}

      {data && items.length > 0 && (
        <div className="flex items-center gap-6 mb-4 text-sm text-text-secondary">
          <span>{data.total ?? items.length} client{(data.total ?? items.length) > 1 ? "s" : ""}</span>
          <span className="text-gray-300">|</span>
          <span>{items.filter((c) => c.email).length} avec email</span>
          <span className="text-gray-300">|</span>
          <span>{items.filter((c) => c.phone).length} avec telephone</span>
        </div>
      )}

      <BatchActionBar
        count={selectedIds.size}
        onExport={handleExportSelection}
        onCreateSegment={handleCreateSegment}
        onClear={clear}
        creatingSegment={creatingSegment}
      />

      <div className="mb-6">
        <SearchInput
          placeholder="Rechercher un client (nom, email, telephone, ville)..."
          onSearch={handleSearch}
        />
      </div>

      <DataTable
        columns={columns}
        data={items}
        loading={isLoading}
        error={error?.message ?? null}
        onRetry={() => mutate()}
        onRowClick={(row) => router.push(`/clients/${row.id}`)}
        getRowHref={(row) => `/clients/${row.id}`}
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
