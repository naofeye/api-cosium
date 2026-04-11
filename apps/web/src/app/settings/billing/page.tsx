"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { fetchJson } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { cn } from "@/lib/utils";
import { AlertTriangle, XCircle } from "lucide-react";
import { PlanSelector, PLANS } from "./components/PlanSelector";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface BillingStatus {
  plan: string;
  status: string;
  trial_days_remaining: number | null;
  stripe_customer_id: string | null;
}

interface CheckoutResponse {
  checkout_url: string;
}

interface CancelResponse {
  status: string;
}

/* ------------------------------------------------------------------ */
/* Status helpers                                                      */
/* ------------------------------------------------------------------ */

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  active: {
    label: "Actif",
    className: "bg-emerald-100 text-emerald-700",
  },
  trialing: {
    label: "Essai gratuit",
    className: "bg-blue-100 text-blue-700",
  },
  past_due: {
    label: "Paiement en retard",
    className: "bg-red-100 text-red-700",
  },
  canceled: {
    label: "Annulé",
    className: "bg-gray-100 text-gray-700",
  },
  unpaid: {
    label: "Impayé",
    className: "bg-red-100 text-red-700",
  },
};

function BillingStatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? {
    label: status,
    className: "bg-gray-100 text-gray-700",
  };
  return (
    <span className={cn("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", cfg.className)}>
      {cfg.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Page component                                                      */
/* ------------------------------------------------------------------ */

export default function BillingPage() {
  const { data: billing, error: swrError, isLoading: loading, mutate } = useSWR<BillingStatus>("/billing/status");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  const error = swrError?.message ?? mutationError ?? null;

  /* ---- Actions ---- */

  async function handleCheckout(planId: string) {
    setCheckoutLoading(planId);
    try {
      const res = await fetchJson<CheckoutResponse>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan: planId }),
      });
      window.location.href = res.checkout_url;
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la création du paiement");
      setCheckoutLoading(null);
    }
  }

  async function handleCancel() {
    setCancelLoading(true);
    setShowCancelDialog(false);
    try {
      await fetchJson<CancelResponse>("/billing/cancel", { method: "POST" });
      await mutate();
    } catch (err: unknown) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de l'annulation");
    } finally {
      setCancelLoading(false);
    }
  }

  /* ---- Render ---- */

  if (loading) return <LoadingState text="Chargement de la facturation..." />;
  if (error && !billing) return <ErrorState message={error} onRetry={() => mutate()} />;
  if (!billing)
    return <ErrorState message="Impossible de charger les informations de facturation." onRetry={() => mutate()} />;

  const currentPlan = PLANS.find((p) => p.id === billing.plan);

  return (
    <PageLayout title="Facturation" breadcrumb={[{ label: "Parametres", href: "/settings" }, { label: "Facturation" }]}>
      <div className="space-y-8">
        {/* Bandeau past_due */}
        {billing.status === "past_due" && (
          <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3">
            <AlertTriangle className="h-5 w-5 shrink-0 text-danger" />
            <p className="text-sm font-medium text-red-800">
              Paiement en retard — veuillez régulariser votre situation pour conserver l'accès à toutes les
              fonctionnalités.
            </p>
          </div>
        )}

        {/* Bandeau canceled */}
        {billing.status === "canceled" && (
          <div className="flex items-center gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3">
            <XCircle className="h-5 w-5 shrink-0 text-warning" />
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">
                Votre abonnement est annulé. Choisissez un plan ci-dessous pour réactiver votre compte.
              </p>
            </div>
          </div>
        )}

        {/* Erreur non bloquante */}
        {error && billing && (
          <div className="flex items-center gap-3 rounded-lg border border-red-300 bg-red-50 px-4 py-3">
            <AlertTriangle className="h-5 w-5 shrink-0 text-danger" />
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Section : Votre abonnement */}
        <section>
          <h1 className="text-2xl font-bold text-gray-900">Facturation</h1>
          <p className="mt-1 text-sm text-text-secondary">Gérez votre abonnement et vos moyens de paiement.</p>
        </section>

        <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800">Votre abonnement</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="text-sm text-text-secondary">Plan actuel</p>
              <p className="mt-1 text-base font-semibold text-gray-900">{currentPlan?.name ?? billing.plan}</p>
            </div>
            <div>
              <p className="text-sm text-text-secondary">Statut</p>
              <div className="mt-1">
                <BillingStatusBadge status={billing.status} />
              </div>
            </div>
            <div>
              <p className="text-sm text-text-secondary">Identifiant Stripe</p>
              <p className="mt-1 text-sm font-mono text-gray-600">{billing.stripe_customer_id ?? "—"}</p>
            </div>
          </div>
          {billing.trial_days_remaining !== null && billing.trial_days_remaining > 0 && (
            <p className="mt-4 text-sm text-blue-700">
              Il vous reste{" "}
              <span className="font-semibold">
                {billing.trial_days_remaining} jour{billing.trial_days_remaining > 1 ? "s" : ""}
              </span>{" "}
              d'essai gratuit.
            </p>
          )}
        </div>

        {/* Section : Changer de plan */}
        <PlanSelector
          currentPlanId={billing.plan}
          currentStatus={billing.status}
          checkoutLoading={checkoutLoading}
          onCheckout={handleCheckout}
        />

        {/* Section : Annuler l'abonnement */}
        {billing.status !== "canceled" && (
          <div className="rounded-xl border border-border bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-800">Annuler l'abonnement</h2>
            <p className="mt-2 text-sm text-text-secondary">
              En annulant votre abonnement, vous perdrez l'accès aux fonctionnalités premium à la fin de la période en
              cours.
            </p>
            <div className="mt-4">
              <Button variant="danger" loading={cancelLoading} onClick={() => setShowCancelDialog(true)}>
                Annuler mon abonnement
              </Button>
            </div>
          </div>
        )}

        {/* Confirm dialog */}
        <ConfirmDialog
          open={showCancelDialog}
          title="Annuler l'abonnement"
          message="Êtes-vous sûr de vouloir annuler votre abonnement ? Vous conserverez l'accès jusqu'à la fin de la période de facturation en cours."
          confirmLabel="Confirmer l'annulation"
          danger
          onConfirm={handleCancel}
          onCancel={() => setShowCancelDialog(false)}
        />
      </div>
    </PageLayout>
  );
}
