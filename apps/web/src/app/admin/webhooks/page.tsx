"use client";

import { useCallback, useState } from "react";
import { ChevronLeft, Copy, Plus, Webhook } from "lucide-react";
import useSWR, { mutate } from "swr";
import Link from "next/link";

import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { DataTable } from "@/components/ui/DataTable";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { LoadingState } from "@/components/ui/LoadingState";
import { fetchJson } from "@/lib/api";

import { CreateSubscriptionDialog } from "./_webhooks/CreateSubscriptionDialog";
import { DeliveryDetailModal } from "./_webhooks/DeliveryDetailModal";
import {
  buildDeliveryColumns,
  buildSubscriptionColumns,
} from "./_webhooks/columns";
import type {
  AllowedEvents,
  Delivery,
  DeliveryList,
  Subscription,
} from "./_webhooks/types";

const fetcher = <T,>(url: string) => fetchJson<T>(url);

export default function WebhooksAdminPage() {
  const { data: subs, error: subsError, isLoading: subsLoading } =
    useSWR<Subscription[]>("/webhooks/subscriptions", fetcher);
  const { data: deliveries } = useSWR<DeliveryList>(
    "/webhooks/deliveries?limit=20",
    fetcher,
    { refreshInterval: 5000 },
  );
  const { data: events } = useSWR<AllowedEvents>("/webhooks/events", fetcher);

  const [showCreate, setShowCreate] = useState(false);
  const [detailDelivery, setDetailDelivery] = useState<Delivery | null>(null);
  const [pingingId, setPingingId] = useState<number | null>(null);
  const [createdSecret, setCreatedSecret] = useState<{
    name: string;
    secret: string;
  } | null>(null);

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
    [refresh],
  );

  const handleDelete = useCallback(
    async (sub: Subscription) => {
      if (
        !confirm(
          `Supprimer la subscription "${sub.name}" ? Toutes les deliveries seront aussi supprimees.`,
        )
      ) {
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
    [refresh],
  );

  const handleTestPing = useCallback(
    async (sub: Subscription) => {
      setPingingId(sub.id);
      try {
        await fetchJson(`/webhooks/subscriptions/${sub.id}/test-ping`, {
          method: "POST",
        });
        refresh();
      } catch {
        /* */
      } finally {
        setPingingId(null);
      }
    },
    [refresh],
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
    [refresh],
  );

  const subColumns = buildSubscriptionColumns({
    onTestPing: handleTestPing,
    onToggle: handleToggle,
    onDelete: handleDelete,
    pingingId,
  });

  const deliveryColumns = buildDeliveryColumns({
    onShowDetail: setDetailDelivery,
    onReplay: handleReplay,
  });

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

      {detailDelivery && (
        <DeliveryDetailModal
          delivery={detailDelivery}
          onClose={() => setDetailDelivery(null)}
        />
      )}
    </PageLayout>
  );
}
