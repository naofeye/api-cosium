"use client";

import { useCallback, useState } from "react";
import { ChevronLeft, Copy, Plus, Trash2, Webhook } from "lucide-react";
import useSWR, { mutate } from "swr";
import Link from "next/link";

import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { fetchJson } from "@/lib/api";

interface Subscription {
  id: number;
  name: string;
  url: string;
  event_types: string[];
  is_active: boolean;
  description: string | null;
  secret_masked: string;
  created_at: string;
  updated_at: string;
}

interface Delivery {
  id: number;
  subscription_id: number;
  event_type: string;
  status: string;
  attempts: number;
  last_status_code: number | null;
  last_error: string | null;
  next_retry_at: string | null;
  delivered_at: string | null;
  duration_ms: number | null;
  created_at: string;
}

interface DeliveryList {
  items: Delivery[];
  total: number;
}

interface AllowedEvents {
  events: string[];
}

const fetcher = <T,>(url: string) => fetchJson<T>(url);

const STATUS_STYLES: Record<string, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  pending: "bg-blue-50 text-blue-700 ring-blue-200",
  retrying: "bg-amber-50 text-amber-700 ring-amber-200",
  failed: "bg-red-50 text-red-700 ring-red-200",
};

function DeliveryStatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? "bg-gray-50 text-gray-700 ring-gray-200";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      {status}
    </span>
  );
}

export default function WebhooksAdminPage() {
  const { data: subs, error: subsError, isLoading: subsLoading } =
    useSWR<Subscription[]>("/webhooks/subscriptions", fetcher);
  const { data: deliveries } = useSWR<DeliveryList>(
    "/webhooks/deliveries?limit=20",
    fetcher,
    { refreshInterval: 5000 }
  );
  const { data: events } = useSWR<AllowedEvents>("/webhooks/events", fetcher);

  const [showCreate, setShowCreate] = useState(false);
  const [createdSecret, setCreatedSecret] = useState<{ name: string; secret: string } | null>(null);

  const refresh = useCallback(() => {
    mutate("/webhooks/subscriptions");
    mutate("/webhooks/deliveries?limit=20");
  }, []);

  const handleToggle = useCallback(
    async (sub: Subscription) => {
      try {
        await fetchJson(`/webhooks/subscriptions/${sub.id}`, {
          method: "PATCH",
          body: JSON.stringify({ is_active: !sub.is_active }),
        });
        refresh();
      } catch {
        // Toast handled globally via api-error event
      }
    },
    [refresh]
  );

  const handleDelete = useCallback(
    async (sub: Subscription) => {
      if (!confirm(`Supprimer la subscription "${sub.name}" ? Toutes les deliveries seront aussi supprimees.`)) {
        return;
      }
      try {
        await fetchJson(`/webhooks/subscriptions/${sub.id}`, {
          method: "DELETE",
        });
        refresh();
      } catch {
        /* global */
      }
    },
    [refresh]
  );

  const handleReplay = useCallback(
    async (delivery: Delivery) => {
      try {
        await fetchJson(`/webhooks/deliveries/${delivery.id}/replay`, {
          method: "POST",
        });
        refresh();
      } catch {
        /* global */
      }
    },
    [refresh]
  );

  const subColumns: Column<Subscription>[] = [
    {
      key: "name",
      header: "Nom",
      render: (s) => (
        <div className="flex flex-col">
          <span className="font-medium text-gray-900">{s.name}</span>
          {s.description && <span className="text-xs text-gray-500">{s.description}</span>}
        </div>
      ),
    },
    {
      key: "url",
      header: "URL",
      render: (s) => (
        <span className="font-mono text-xs text-gray-600 break-all">{s.url}</span>
      ),
    },
    {
      key: "event_types",
      header: "Evenements",
      render: (s) => (
        <div className="flex flex-wrap gap-1">
          {s.event_types.map((e) => (
            <span
              key={e}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
            >
              {e}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: "is_active",
      header: "Statut",
      render: (s) => (
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
            s.is_active
              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
              : "bg-gray-50 text-gray-500 ring-gray-200"
          }`}
        >
          {s.is_active ? "Actif" : "Inactif"}
        </span>
      ),
    },
    {
      key: "secret_masked",
      header: "Secret",
      render: (s) => <span className="font-mono text-xs">{s.secret_masked}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (s) => (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => handleToggle(s)}>
            {s.is_active ? "Desactiver" : "Activer"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleDelete(s)}
            aria-label={`Supprimer ${s.name}`}
          >
            <Trash2 size={14} />
          </Button>
        </div>
      ),
    },
  ];

  const deliveryColumns: Column<Delivery>[] = [
    {
      key: "created_at",
      header: "Date",
      render: (d) => <DateDisplay date={d.created_at} />,
    },
    {
      key: "event_type",
      header: "Evenement",
      render: (d) => (
        <span className="font-mono text-xs">{d.event_type}</span>
      ),
    },
    {
      key: "status",
      header: "Statut",
      render: (d) => <DeliveryStatusBadge status={d.status} />,
    },
    {
      key: "attempts",
      header: "Tentatives",
      render: (d) => <span className="font-mono">{d.attempts}</span>,
    },
    {
      key: "last_status_code",
      header: "Code HTTP",
      render: (d) =>
        d.last_status_code !== null ? (
          <span className="font-mono">{d.last_status_code}</span>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
    {
      key: "duration_ms",
      header: "Duree",
      render: (d) =>
        d.duration_ms !== null ? (
          <span className="font-mono text-xs">{d.duration_ms} ms</span>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (d) =>
        d.status === "failed" ? (
          <Button variant="outline" size="sm" onClick={() => handleReplay(d)}>
            Rejouer
          </Button>
        ) : null,
    },
  ];

  return (
    <PageLayout
      title="Webhooks sortants"
      description="Notifications HTTP push vers vos systemes tiers (CRM, comptabilite, automatisation)."
      breadcrumb={[
        { label: "Administration", href: "/admin" },
        { label: "Webhooks" },
      ]}
      actions={
        <Button onClick={() => setShowCreate(true)} aria-label="Nouvelle subscription">
          <Plus size={16} className="mr-1" />
          Nouvelle subscription
        </Button>
      }
    >
      {createdSecret && (
        <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <div className="flex items-start gap-3">
            <Webhook className="text-amber-700 mt-0.5" size={20} />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-900">
                Secret HMAC genere — copiez-le maintenant
              </h3>
              <p className="text-sm text-amber-800 mt-1">
                Cette valeur ne sera plus affichee. Stockez-la chez le destinataire pour
                verifier la signature des payloads.
              </p>
              <div className="mt-3 flex gap-2 items-center">
                <code className="flex-1 bg-white border border-amber-200 rounded px-3 py-2 font-mono text-sm break-all">
                  {createdSecret.secret}
                </code>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigator.clipboard.writeText(createdSecret.secret)}
                  aria-label="Copier le secret"
                >
                  <Copy size={14} />
                </Button>
                <Button variant="outline" size="sm" onClick={() => setCreatedSecret(null)}>
                  Fermer
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <section className="mb-10">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Subscriptions</h2>
        {subsLoading ? (
          <LoadingState text="Chargement des subscriptions..." />
        ) : subsError ? (
          <ErrorState
            message="Impossible de charger les subscriptions."
            onRetry={() => mutate("/webhooks/subscriptions")}
          />
        ) : (subs ?? []).length === 0 ? (
          <EmptyState
            icon={Webhook}
            title="Aucune subscription"
            description="Creez votre premiere subscription pour commencer a notifier des systemes tiers."
            action={
              <Button onClick={() => setShowCreate(true)}>Creer une subscription</Button>
            }
          />
        ) : (
          <DataTable columns={subColumns} data={subs ?? []} />
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Deliveries recentes (20 dernieres, refresh 5s)
        </h2>
        {(deliveries?.items ?? []).length === 0 ? (
          <EmptyState
            icon={Webhook}
            title="Aucune livraison"
            description="Les notifications apparaitront ici quand des evenements se produiront."
          />
        ) : (
          <DataTable columns={deliveryColumns} data={deliveries?.items ?? []} />
        )}
      </section>

      {showCreate && (
        <CreateSubscriptionDialog
          allowedEvents={events?.events ?? []}
          onClose={() => setShowCreate(false)}
          onCreated={(name, secret) => {
            setCreatedSecret({ name, secret });
            setShowCreate(false);
            refresh();
          }}
        />
      )}

      <div className="mt-8 text-xs text-gray-500">
        <Link href="/admin" className="inline-flex items-center gap-1 hover:underline">
          <ChevronLeft size={14} /> Retour Administration
        </Link>
      </div>
    </PageLayout>
  );
}

interface CreateProps {
  allowedEvents: string[];
  onClose: () => void;
  onCreated: (name: string, secret: string) => void;
}

function CreateSubscriptionDialog({ allowedEvents, onClose, onCreated }: CreateProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("https://");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (event: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(event)) next.delete(event);
      else next.add(event);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (selected.size === 0) {
      setError("Selectionnez au moins un evenement.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await fetchJson<{ name: string; secret: string }>(
        "/webhooks/subscriptions",
        {
          method: "POST",
          body: JSON.stringify({
            name: name.trim(),
            url: url.trim(),
            event_types: Array.from(selected),
            description: description.trim() || undefined,
          }),
        }
      );
      onCreated(result.name, result.secret);
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
      aria-label="Nouvelle subscription webhook"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6">
          <h2 className="text-lg font-semibold mb-4">Nouvelle subscription webhook</h2>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Nom *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                placeholder="Ex: Notif comptabilite"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">URL HTTPS *</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                placeholder="https://exemple.com/optiflow-hooks"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
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
                Evenements ecoutes * ({selected.size} selectionne{selected.size > 1 ? "s" : ""})
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto border border-gray-200 rounded-lg p-3">
                {allowedEvents.map((event) => (
                  <label
                    key={event}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 rounded px-2 py-1"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(event)}
                      onChange={() => toggle(event)}
                    />
                    <span className="font-mono text-xs">{event}</span>
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
            <Button type="submit" disabled={submitting || !name || !url || selected.size === 0}>
              {submitting ? "Creation..." : "Creer la subscription"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
