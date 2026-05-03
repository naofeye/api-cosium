"use client";

import { useCallback, useState } from "react";
import { Code2, Copy, KeyRound, Plus, Trash2 } from "lucide-react";
import useSWR, { mutate } from "swr";

import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { fetchJson } from "@/lib/api";

interface ApiToken {
  id: number;
  tenant_id: number;
  name: string;
  prefix: string;
  scopes: string[];
  description: string | null;
  expires_at: string | null;
  revoked: boolean;
  last_used_at: string | null;
  created_at: string;
}

interface AllowedScopesResponse {
  scopes: string[];
}

const fetcher = <T,>(url: string) => fetchJson<T>(url);

export default function ApiPubliqueAdminPage() {
  const { data: tokens, error, isLoading } = useSWR<ApiToken[]>(
    "/admin/api-tokens",
    fetcher,
  );
  const { data: scopesData } = useSWR<AllowedScopesResponse>(
    "/admin/api-tokens/scopes",
    fetcher,
  );

  const [showCreate, setShowCreate] = useState(false);
  const [createdToken, setCreatedToken] = useState<{ name: string; token: string } | null>(null);

  const refresh = useCallback(() => mutate("/admin/api-tokens"), []);

  const handleRevoke = useCallback(
    async (token: ApiToken) => {
      try {
        await fetchJson(`/admin/api-tokens/${token.id}`, {
          method: "PATCH",
          body: JSON.stringify({ revoked: !token.revoked }),
        });
        refresh();
      } catch {
        /* api-error toast global */
      }
    },
    [refresh],
  );

  const handleDelete = useCallback(
    async (token: ApiToken) => {
      if (!confirm(`Supprimer definitivement le token "${token.name}" ?`)) return;
      try {
        await fetchJson(`/admin/api-tokens/${token.id}`, { method: "DELETE" });
        refresh();
      } catch {
        /* */
      }
    },
    [refresh],
  );

  const columns: Column<ApiToken>[] = [
    {
      key: "name",
      header: "Nom",
      render: (t) => (
        <div className="flex flex-col">
          <span className="font-medium text-gray-900">{t.name}</span>
          {t.description && (
            <span className="text-xs text-gray-500">{t.description}</span>
          )}
        </div>
      ),
    },
    {
      key: "prefix",
      header: "Prefixe",
      render: (t) => (
        <code className="text-xs bg-gray-100 px-2 py-0.5 rounded font-mono">
          {t.prefix}***
        </code>
      ),
    },
    {
      key: "scopes",
      header: "Scopes",
      render: (t) => (
        <div className="flex flex-wrap gap-1">
          {t.scopes.map((s) => (
            <span
              key={s}
              className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-mono"
            >
              {s}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: "revoked",
      header: "Statut",
      render: (t) => (
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
            t.revoked
              ? "bg-red-50 text-red-700 ring-red-200"
              : "bg-emerald-50 text-emerald-700 ring-emerald-200"
          }`}
        >
          {t.revoked ? "Revoque" : "Actif"}
        </span>
      ),
    },
    {
      key: "last_used_at",
      header: "Derniere utilisation",
      render: (t) =>
        t.last_used_at ? (
          <DateDisplay date={t.last_used_at} />
        ) : (
          <span className="text-gray-400 text-xs">Jamais</span>
        ),
    },
    {
      key: "expires_at",
      header: "Expire le",
      render: (t) =>
        t.expires_at ? (
          <DateDisplay date={t.expires_at} />
        ) : (
          <span className="text-gray-400 text-xs">Jamais</span>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (t) => (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => handleRevoke(t)}>
            {t.revoked ? "Reactiver" : "Revoquer"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDelete(t)}
            aria-label={`Supprimer ${t.name}`}
          >
            <Trash2 size={14} />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageLayout
      title="API publique v1"
      description="Tokens d'acces pour vos integrations partenaires (mutuelles, plateformes tiers payant, comptabilite)."
      breadcrumb={[
        { label: "Administration", href: "/admin" },
        { label: "API publique" },
      ]}
      actions={
        <Button onClick={() => setShowCreate(true)}>
          <Plus size={16} className="mr-1" />
          Nouveau token
        </Button>
      }
    >
      {createdToken && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <KeyRound className="text-amber-700 mt-0.5" size={20} />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900">
                Token genere — copiez-le maintenant
              </h3>
              <p className="text-sm text-amber-800 mt-1">
                Cette valeur ne sera plus jamais affichee. Stockez-la dans le
                vault de votre integration partenaire (variable d&apos;env).
              </p>
              <div className="mt-3 flex items-center gap-2">
                <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 font-mono text-sm break-all">
                  {createdToken.token}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(createdToken.token)}
                  aria-label="Copier le token"
                >
                  <Copy size={14} />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCreatedToken(null)}
                >
                  Fermer
                </Button>
              </div>
              <div className="mt-3 text-xs text-amber-800">
                <p className="font-medium">Exemple d&apos;utilisation :</p>
                <code className="block mt-1 bg-white border border-amber-200 rounded p-2 font-mono">
                  curl -H &quot;Authorization: Bearer {createdToken.token.slice(0, 20)}...&quot; https://cosium.ia.coging.com/api/public/v1/clients
                </code>
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="mb-8">
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
          <div className="flex items-start gap-2">
            <Code2 size={18} className="mt-0.5 shrink-0" />
            <div>
              <p className="font-medium">API publique read-only</p>
              <p className="mt-1">
                Endpoints disponibles : <code>GET /api/public/v1/clients</code>,{" "}
                <code>/devis</code>, <code>/factures</code>,{" "}
                <code>/pec-requests</code>. Auth :{" "}
                <code>Authorization: Bearer &lt;token&gt;</code>.
              </p>
              <p className="mt-1">
                Documentation Swagger : <a href="/api/v1/docs" className="underline" target="_blank" rel="noopener noreferrer">/api/v1/docs</a>
              </p>
            </div>
          </div>
        </div>
      </section>

      {isLoading ? (
        <LoadingState text="Chargement des tokens..." />
      ) : error ? (
        <ErrorState
          message="Impossible de charger les tokens."
          onRetry={() => mutate("/admin/api-tokens")}
        />
      ) : (tokens ?? []).length === 0 ? (
        <EmptyState
          icon={KeyRound}
          title="Aucun token"
          description="Creez votre premier token pour permettre a une integration partenaire d'acceder en lecture aux donnees du tenant."
          action={
            <Button onClick={() => setShowCreate(true)}>Creer un token</Button>
          }
        />
      ) : (
        <DataTable columns={columns} data={tokens ?? []} />
      )}

      {showCreate && (
        <CreateTokenDialog
          allowedScopes={scopesData?.scopes ?? []}
          onClose={() => setShowCreate(false)}
          onCreated={(name, token) => {
            setCreatedToken({ name, token });
            setShowCreate(false);
            refresh();
          }}
        />
      )}
    </PageLayout>
  );
}

interface CreateProps {
  allowedScopes: string[];
  onClose: () => void;
  onCreated: (name: string, token: string) => void;
}

function CreateTokenDialog({ allowedScopes, onClose, onCreated }: CreateProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [scopes, setScopes] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (scope: string) => {
    setScopes((prev) => {
      const next = new Set(prev);
      if (next.has(scope)) next.delete(scope);
      else next.add(scope);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (scopes.size === 0) {
      setError("Selectionnez au moins un scope.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await fetchJson<{ name: string; token: string }>(
        "/admin/api-tokens",
        {
          method: "POST",
          body: JSON.stringify({
            name: name.trim(),
            scopes: Array.from(scopes),
            description: description.trim() || undefined,
          }),
        },
      );
      onCreated(result.name, result.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Echec de la creation.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Nouveau token API"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full">
        <form onSubmit={handleSubmit} className="p-6">
          <h2 className="text-lg font-semibold mb-4">Nouveau token API</h2>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Nom *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                placeholder="Ex: Integration mutuelle Almerys"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Description (optionnel)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={500}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Scopes * ({scopes.size} selectionne{scopes.size > 1 ? "s" : ""})
              </label>
              <div className="grid grid-cols-2 gap-2 border border-gray-200 rounded-lg p-3">
                {allowedScopes.map((scope) => (
                  <label
                    key={scope}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 rounded px-2 py-1"
                  >
                    <input
                      type="checkbox"
                      checked={scopes.has(scope)}
                      onChange={() => toggle(scope)}
                    />
                    <code className="text-xs">{scope}</code>
                  </label>
                ))}
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              Annuler
            </Button>
            <Button type="submit" disabled={submitting || !name || scopes.size === 0}>
              {submitting ? "Creation..." : "Creer le token"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
