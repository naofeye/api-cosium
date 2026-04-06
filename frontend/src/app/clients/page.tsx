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
import { Download, Upload, AlertTriangle, Users, FileDown, FileSpreadsheet, X, CheckCircle, XCircle, AlertCircle, Merge, ArrowRight } from "lucide-react";
import type { Customer } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

interface ImportError {
  line: number;
  reason: string;
}

interface ImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors: ImportError[];
}

interface DuplicateGroup {
  name: string;
  count: number;
  clients: Customer[];
}

interface MergeResult {
  kept_client: Customer;
  cases_transferred: number;
  interactions_transferred: number;
  pec_transferred: number;
  marketing_transferred: number;
  cosium_data_transferred: number;
  fields_filled: string[];
  merged_client_deleted: boolean;
}

const FIELD_LABELS: Record<string, string> = {
  first_name: "Prenom",
  last_name: "Nom",
  email: "Email",
  phone: "Telephone",
  birth_date: "Date de naissance",
  address: "Adresse",
  city: "Ville",
  postal_code: "Code postal",
  social_security_number: "N. Secu",
  notes: "Notes",
  avatar_url: "Photo",
  created_at: "Cree le",
};

const COMPARE_FIELDS = ["first_name", "last_name", "email", "phone", "birth_date", "address", "city", "postal_code", "social_security_number", "notes"] as const;

export default function ClientsPage() {
  const router = useRouter();
  const { toast } = useToast();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [importing, setImporting] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [duplicates, setDuplicates] = useState<DuplicateGroup[]>([]);
  const [dupesPending, startDupesTransition] = useTransition();
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [compareGroup, setCompareGroup] = useState<DuplicateGroup | null>(null);
  const [merging, setMerging] = useState(false);

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

  const handleExportComplet = () => {
    window.open(`${API_BASE}/exports/clients-complet`, "_blank");
  };

  const handleDownloadTemplate = () => {
    window.open(`${API_BASE}/clients/import/template`, "_blank");
  };

  const handleImportFile = async (file: File) => {
    const ext = file.name.toLowerCase().split(".").pop();
    if (!["csv", "xlsx", "xls"].includes(ext || "")) {
      toast("Le fichier doit etre au format CSV ou Excel (.xlsx).", "error");
      return;
    }
    setImporting(true);
    setImportResult(null);
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
      setImportResult(importData);
      mutate();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de l'import", "error");
    } finally {
      setImporting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleImportFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImportFile(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleShowDuplicates = () => {
    if (showDuplicates) {
      setShowDuplicates(false);
      setCompareGroup(null);
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

  const handleMerge = async (keepId: number, mergeId: number) => {
    setMerging(true);
    try {
      const result = await fetchJson<MergeResult>("/clients/merge", {
        method: "POST",
        body: JSON.stringify({ keep_id: keepId, merge_id: mergeId }),
      });
      const totalTransferred =
        result.cases_transferred +
        result.interactions_transferred +
        result.pec_transferred +
        result.marketing_transferred;
      toast(
        `Fusion reussie. ${totalTransferred} element(s) transfere(s)${result.fields_filled.length > 0 ? `, ${result.fields_filled.length} champ(s) complete(s)` : ""}.`,
        "success"
      );
      setCompareGroup(null);
      // Refresh duplicates list
      try {
        const updated = await fetchJson<DuplicateGroup[]>("/clients/duplicates");
        setDuplicates(updated);
      } catch {
        setShowDuplicates(false);
      }
      mutate();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la fusion", "error");
    } finally {
      setMerging(false);
    }
  };

  const getFieldValue = (client: Customer, field: string): string => {
    const val = client[field as keyof Customer];
    if (val === null || val === undefined || val === "") return "";
    return String(val);
  };

  const getCompleteness = (client: Customer): number => {
    let filled = 0;
    for (const f of COMPARE_FIELDS) {
      if (getFieldValue(client, f)) filled++;
    }
    return Math.round((filled / COMPARE_FIELDS.length) * 100);
  };

  const columns: Column<Customer>[] = [
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
          <Button variant="outline" onClick={() => { setShowImportDialog(true); setImportResult(null); }}>
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
      {/* Import Dialog */}
      {showImportDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setShowImportDialog(false)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Importer des clients</h2>
              <button onClick={() => setShowImportDialog(false)} className="text-gray-400 hover:text-gray-600" aria-label="Fermer">
                <X className="h-5 w-5" />
              </button>
            </div>

            {!importResult ? (
              <>
                <p className="text-sm text-gray-500 mb-4">
                  Glissez-deposez un fichier CSV ou Excel (.xlsx), ou cliquez pour parcourir.
                  Les colonnes reconnues : Nom, Prenom, Email, Telephone, Date de naissance, Adresse, Ville, Code postal, N° Secu.
                </p>

                <div
                  className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-colors cursor-pointer ${
                    dragOver ? "border-blue-500 bg-blue-50" : "border-gray-300 hover:border-gray-400"
                  }`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  aria-label="Zone de depot de fichier"
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
                >
                  {importing ? (
                    <>
                      <div className="h-8 w-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
                      <p className="mt-3 text-sm text-gray-600">Import en cours...</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-400" />
                      <p className="mt-3 text-sm text-gray-500">Glissez un fichier ici ou cliquez pour parcourir</p>
                      <p className="mt-1 text-xs text-gray-400">Formats acceptes : CSV, Excel (.xlsx)</p>
                    </>
                  )}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                </div>

                <div className="mt-4 flex justify-between items-center">
                  <button
                    onClick={handleDownloadTemplate}
                    className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                  >
                    <FileDown className="h-4 w-4" />
                    Telecharger le modele CSV
                  </button>
                  <Button variant="outline" onClick={() => setShowImportDialog(false)}>
                    Fermer
                  </Button>
                </div>
              </>
            ) : (
              <>
                {/* Import result report */}
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-lg bg-emerald-50 border border-emerald-200 p-3 text-center">
                      <CheckCircle className="h-5 w-5 text-emerald-600 mx-auto mb-1" />
                      <p className="text-xl font-bold text-emerald-700">{importResult.imported}</p>
                      <p className="text-xs text-emerald-600">Importes</p>
                    </div>
                    <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-center">
                      <AlertCircle className="h-5 w-5 text-blue-600 mx-auto mb-1" />
                      <p className="text-xl font-bold text-blue-700">{importResult.updated}</p>
                      <p className="text-xs text-blue-600">Mis a jour</p>
                    </div>
                    <div className="rounded-lg bg-gray-50 border border-gray-200 p-3 text-center">
                      <XCircle className="h-5 w-5 text-gray-500 mx-auto mb-1" />
                      <p className="text-xl font-bold text-gray-600">{importResult.skipped}</p>
                      <p className="text-xs text-gray-500">Ignores</p>
                    </div>
                  </div>

                  {importResult.errors.length > 0 && (
                    <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
                      <h4 className="text-sm font-semibold text-amber-800 mb-2 flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4" />
                        {importResult.errors.length} avertissement{importResult.errors.length > 1 ? "s" : ""}
                      </h4>
                      <div className="max-h-40 overflow-y-auto space-y-1">
                        {importResult.errors.map((err, idx) => (
                          <p key={idx} className="text-xs text-amber-700">
                            <span className="font-mono font-medium">Ligne {err.line}</span> : {err.reason}
                          </p>
                        ))}
                      </div>
                    </div>
                  )}

                  {importResult.errors.length === 0 && importResult.imported > 0 && (
                    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-center">
                      <p className="text-sm text-emerald-700">Import termine avec succes !</p>
                    </div>
                  )}
                </div>

                <div className="mt-4 flex justify-end gap-2">
                  <Button variant="outline" onClick={() => { setImportResult(null); }}>
                    Importer un autre fichier
                  </Button>
                  <Button onClick={() => setShowImportDialog(false)}>
                    Fermer
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

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
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-medium text-gray-800">
                      {group.name} ({group.count} occurrences)
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => setCompareGroup(compareGroup?.name === group.name ? null : group)}
                    >
                      <Merge className="h-3.5 w-3.5 mr-1" />
                      {compareGroup?.name === group.name ? "Fermer" : "Comparer / Fusionner"}
                    </Button>
                  </div>
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

                  {/* Side-by-side comparison view */}
                  {compareGroup?.name === group.name && group.clients.length >= 2 && (
                    <div className="mt-4 border-t border-amber-100 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-3">Comparaison des fiches</h4>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b border-gray-200">
                              <th className="text-left py-2 px-2 text-gray-500 font-medium w-32">Champ</th>
                              {group.clients.map((c) => (
                                <th key={c.id} className="text-left py-2 px-2">
                                  <div className="flex items-center gap-1">
                                    <span className="font-mono text-text-secondary">#{c.id}</span>
                                    <span className="text-xs px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 font-medium">
                                      {getCompleteness(c)}%
                                    </span>
                                  </div>
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {COMPARE_FIELDS.map((field) => {
                              const values = group.clients.map((c) => getFieldValue(c, field));
                              const allSame = values.every((v) => v === values[0]);
                              return (
                                <tr key={field} className={`border-b border-gray-100 ${!allSame ? "bg-amber-50/50" : ""}`}>
                                  <td className="py-1.5 px-2 text-gray-500 font-medium">
                                    {FIELD_LABELS[field] || field}
                                  </td>
                                  {group.clients.map((c) => {
                                    const val = getFieldValue(c, field);
                                    return (
                                      <td key={c.id} className="py-1.5 px-2">
                                        {val ? (
                                          <span className="text-gray-800">{val}</span>
                                        ) : (
                                          <span className="text-gray-300 italic">vide</span>
                                        )}
                                      </td>
                                    );
                                  })}
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>

                      {/* Merge actions */}
                      <div className="mt-4 flex flex-wrap gap-2">
                        {group.clients.map((keepClient) => {
                          const otherClients = group.clients.filter((c) => c.id !== keepClient.id);
                          const mostComplete = group.clients.reduce((best, c) =>
                            getCompleteness(c) > getCompleteness(best) ? c : best
                          );
                          const isRecommended = keepClient.id === mostComplete.id;
                          return otherClients.length === 1 ? (
                            <Button
                              key={keepClient.id}
                              variant={isRecommended ? "primary" : "outline"}
                              disabled={merging}
                              onClick={() => {
                                if (confirm(
                                  `Fusionner #${otherClients[0].id} dans #${keepClient.id} ?\n\nLes dossiers, interactions et donnees de #${otherClients[0].id} seront transferes vers #${keepClient.id}.\n#${otherClients[0].id} sera supprime.`
                                )) {
                                  handleMerge(keepClient.id, otherClients[0].id);
                                }
                              }}
                            >
                              {merging ? "Fusion..." : (
                                <>
                                  Garder #{keepClient.id}
                                  <ArrowRight className="h-3.5 w-3.5 mx-1" />
                                  Supprimer #{otherClients[0].id}
                                  {isRecommended && <span className="ml-1 text-xs opacity-75">(recommande)</span>}
                                </>
                              )}
                            </Button>
                          ) : null;
                        })}
                      </div>
                      {group.clients.length > 2 && (
                        <p className="mt-2 text-xs text-amber-700">
                          Ce groupe contient plus de 2 clients. Veuillez les fusionner deux par deux.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
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
