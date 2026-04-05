"use client";

import { useCallback, useRef, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { PageLayout } from "@/components/layout/PageLayout";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { useToast } from "@/components/ui/Toast";
import { useClients } from "@/lib/hooks/use-api";
import { exportToCsv } from "@/lib/export-csv";
import { fetchJson } from "@/lib/api";
import Link from "next/link";
import { Download, Upload, AlertTriangle } from "lucide-react";
import type { Customer } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface ImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

interface DuplicateGroup {
  name: string;
  count: number;
  clients: Customer[];
}

export default function ClientsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [importing, setImporting] = useState(false);
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [dupesPending, startDupesTransition] = useTransition();
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      String(c.id),
      c.last_name,
      c.first_name,
      c.phone || "",
      c.email || "",
      c.city || "",
      c.created_at || "",
    ]);
    exportToCsv("clients.csv", headers, rows);
  };

  const handleImportClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      toast("Le fichier doit etre au format CSV.", "error");
      return;
    }
    setImporting(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const result = await fetch(`${API_BASE}/clients/import`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      if (!result.ok) {
        const errData = await result.json().catch(() => ({}));
        throw new Error(errData?.error?.message || `Erreur ${result.status}`);
      }
      const importData: ImportResult = await result.json();
      toast(
        `Import termine : ${importData.imported} importe(s), ${importData.skipped} ignore(s)${importData.errors.length > 0 ? `. ${importData.errors.length} erreur(s).` : ""}`,
        importData.errors.length > 0 ? "warning" : "success",
      );
      mutate();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de l'import", "error");
    } finally {
      setImporting(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
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

  const columns: Column<Customer>[] = [
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    {
      key: "name",
      header: "Nom",
      render: (row) => (
        <div className="flex items-center gap-2">
          {row.avatar_url ? (
            <img src={`${API_BASE}/clients/${row.id}/avatar`} alt="" className="h-8 w-8 rounded-full object-cover" />
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
          <Button variant="outline" onClick={handleImportClick} disabled={importing}>
            <Upload className="h-4 w-4 mr-1" />
            {importing ? "Import en cours..." : "Importer CSV"}
          </Button>
          <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
          <Button variant="outline" onClick={handleExportCsv}>
            <Download className="h-4 w-4 mr-1" /> Exporter CSV
          </Button>
          <Link href="/clients/new">
            <Button>Nouveau client</Button>
          </Link>
        </div>
      }
    >
      {/* Duplicate detection panel */}
      {showDuplicates && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <h3 className="text-sm font-semibold text-amber-800 mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {duplicates.length} groupe(s) de doublons detecte(s)
          </h3>
          {duplicates.length === 0 ? (
            <p className="text-sm text-amber-700">Aucun doublon detecte.</p>
          ) : (
            <div className="space-y-3">
              {duplicates.map((group, idx) => (
                <div key={idx} className="rounded-lg bg-white border border-amber-100 p-3">
                  <p className="text-sm font-medium text-gray-800 mb-2">
                    {group.name} ({group.count} occurrences)
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                    {group.clients.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => router.push(`/clients/${c.id}`)}
                        className="text-left text-xs bg-gray-50 rounded p-2 hover:bg-gray-100 transition-colors"
                      >
                        <span className="font-mono text-text-secondary">#{c.id}</span>{" "}
                        <span>{c.email || "pas d'email"}</span>{" "}
                        <span className="text-text-secondary">{c.phone || ""}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
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
        emptyDescription="Commencez par creer votre premier client."
        emptyAction={
          <Link href="/clients/new">
            <Button>Creer un client</Button>
          </Link>
        }
        page={page}
        pageSize={25}
        total={data?.total}
        onPageChange={setPage}
      />
    </PageLayout>
  );
}
