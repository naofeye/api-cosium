"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { API_BASE } from "@/lib/api";
import {
  Upload,
  X,
  CheckCircle,
  XCircle,
  AlertCircle,
  AlertTriangle,
  FileDown,
} from "lucide-react";

export interface ImportError {
  line: number;
  reason: string;
}

export interface ImportResult {
  imported: number;
  updated: number;
  skipped: number;
  errors: ImportError[];
}

interface ImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

export function ImportDialog({ open, onClose, onImported }: ImportDialogProps) {
  const { toast } = useToast();
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!open) return null;

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
      onImported();
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

  const handleDownloadTemplate = () => {
    window.open(`${API_BASE}/clients/import/template`, "_blank");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">Importer des clients</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600" aria-label="Fermer">
            <X className="h-5 w-5" />
          </button>
        </div>

        {!importResult ? (
          <>
            <p className="text-sm text-gray-500 mb-4">
              Glissez-deposez un fichier CSV ou Excel (.xlsx), ou cliquez pour parcourir.
              Les colonnes reconnues : Nom, Prenom, Email, Telephone, Date de naissance, Adresse, Ville, Code postal, N. Secu.
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
              <Button variant="outline" onClick={onClose}>
                Fermer
              </Button>
            </div>
          </>
        ) : (
          <>
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
              <Button variant="outline" onClick={() => setImportResult(null)}>
                Importer un autre fichier
              </Button>
              <Button onClick={onClose}>
                Fermer
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
