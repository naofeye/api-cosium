"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { AlertTriangle, Merge, ArrowRight } from "lucide-react";
import type { Customer } from "@/lib/types";

export interface DuplicateGroup {
  name: string;
  count: number;
  clients: Customer[];
}

interface MergePreview {
  keepId: number;
  mergeId: number;
  keepName: string;
  mergeName: string;
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

const COMPARE_FIELDS = [
  "first_name", "last_name", "email", "phone", "birth_date",
  "address", "city", "postal_code", "social_security_number", "notes",
] as const;

function getFieldValue(client: Customer, field: string): string {
  const val = client[field as keyof Customer];
  if (val === null || val === undefined || val === "") return "";
  return String(val);
}

function getCompleteness(client: Customer): number {
  let filled = 0;
  for (const f of COMPARE_FIELDS) {
    if (getFieldValue(client, f)) filled++;
  }
  return Math.round((filled / COMPARE_FIELDS.length) * 100);
}

interface DuplicatesPanelProps {
  duplicates: DuplicateGroup[];
  onRefresh: () => void;
  onDataChanged: () => void;
}

export function DuplicatesPanel({ duplicates, onRefresh, onDataChanged }: DuplicatesPanelProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [compareGroup, setCompareGroup] = useState<DuplicateGroup | null>(null);
  const [merging, setMerging] = useState(false);
  const [mergePreview, setMergePreview] = useState<MergePreview | null>(null);

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
      onRefresh();
      onDataChanged();
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la fusion", "error");
    } finally {
      setMerging(false);
    }
  };

  return (
    <>
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
                          onClick={() => setMergePreview({
                            keepId: keepClient.id,
                            mergeId: otherClients[0].id,
                            keepName: `${keepClient.last_name} ${keepClient.first_name}`,
                            mergeName: `${otherClients[0].last_name} ${otherClients[0].first_name}`,
                          })}
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

      {/* Merge Preview Dialog */}
      {mergePreview && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => !merging && setMergePreview(null)}>
          <div className="bg-bg-card rounded-xl shadow-xl border border-border p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Merge className="h-5 w-5 text-primary" />
              Confirmer la fusion
            </h3>

            <div className="space-y-3 mb-6">
              <div className="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 p-3">
                <p className="text-sm font-medium text-emerald-800 dark:text-emerald-300">Conserver : #{mergePreview.keepId} — {mergePreview.keepName}</p>
              </div>
              <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3">
                <p className="text-sm font-medium text-red-800 dark:text-red-300">Supprimer : #{mergePreview.mergeId} — {mergePreview.mergeName}</p>
              </div>
            </div>

            <div className="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-3 mb-6">
              <p className="text-sm text-amber-800 dark:text-amber-300">
                <strong>Cette action va :</strong>
              </p>
              <ul className="text-sm text-amber-700 dark:text-amber-400 mt-1 list-disc list-inside space-y-0.5">
                <li>Transferer tous les dossiers, documents et paiements</li>
                <li>Transferer les interactions et donnees PEC</li>
                <li>Completer les champs manquants du client conserve</li>
                <li>Supprimer definitivement le client #{mergePreview.mergeId}</li>
              </ul>
            </div>

            <div className="flex justify-end gap-3">
              <Button variant="outline" onClick={() => setMergePreview(null)} disabled={merging}>
                Annuler
              </Button>
              <Button
                variant="primary"
                onClick={() => {
                  handleMerge(mergePreview.keepId, mergePreview.mergeId);
                  setMergePreview(null);
                }}
                disabled={merging}
              >
                {merging ? "Fusion en cours..." : "Confirmer la fusion"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
