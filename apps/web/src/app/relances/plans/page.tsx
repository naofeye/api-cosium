"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { reminderPlanSchema, type ReminderPlanFormData } from "@/lib/schemas/reminder";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchJson } from "@/lib/api";
import { Plus, Play, ToggleLeft, ToggleRight } from "lucide-react";

interface Plan {
  id: number;
  name: string;
  payer_type: string;
  rules_json: string;
  channel_sequence: string;
  interval_days: number;
  is_active: boolean;
}

export default function PlansPage() {
  const { data: plans, error: plansErr, isLoading, mutate } = useSWR<Plan[]>("/reminders/plans");
  const [showForm, setShowForm] = useState(false);
  const [minDays, setMinDays] = useState(7);
  const [minAmount, setMinAmount] = useState(0);
  const [maxReminders, setMaxReminders] = useState(3);
  const [error, setError] = useState<string | null>(null);
  const [inFlightId, setInFlightId] = useState<number | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting, isValid },
  } = useForm<ReminderPlanFormData>({
    resolver: zodResolver(reminderPlanSchema),
    mode: "onChange",
    defaultValues: {
      name: "",
      payer_type: "client",
      interval_days: 7,
      is_active: true,
    },
  });

  const onSubmit = async (data: ReminderPlanFormData) => {
    try {
      await fetchJson("/reminders/plans", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          payer_type: data.payer_type,
          rules_json: { min_days_overdue: minDays, min_amount: minAmount, max_reminders: maxReminders },
          channel_sequence: ["email", "courrier", "telephone"],
          interval_days: data.interval_days,
        }),
      });
      setShowForm(false);
      reset();
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    }
  };

  const togglePlan = async (planId: number, isActive: boolean) => {
    if (inFlightId !== null) return;
    setInFlightId(planId);
    try {
      await fetchJson(`/reminders/plans/${planId}/toggle?is_active=${!isActive}`, { method: "PATCH" });
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setInFlightId(null);
    }
  };

  const executePlan = async (planId: number) => {
    if (inFlightId !== null) return;
    setInFlightId(planId);
    try {
      await fetchJson(`/reminders/plans/${planId}/execute`, { method: "POST" });
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setInFlightId(null);
    }
  };

  const displayError = plansErr?.message ?? error;

  if (isLoading)
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Plans" }]}>
        <LoadingState text="Chargement des plans..." />
      </PageLayout>
    );
  if (displayError)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Plans" }]}>
        <ErrorState
          message={displayError}
          onRetry={() => {
            setError(null);
            mutate();
          }}
        />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Plans de relance"
      description="Configuration des plans de relance automatiques"
      breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Plans" }]}
      actions={
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1" /> Nouveau plan
        </Button>
      }
    >
      {showForm && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6"
        >
          <h3 className="text-lg font-semibold text-text-primary mb-4">Nouveau plan de relance</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom *</label>
              <input
                type="text"
                {...register("name")}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Plan client standard"
              />
              {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type payeur *</label>
              <select {...register("payer_type")} className="w-full rounded-lg border border-border px-3 py-2 text-sm">
                <option value="client">Client</option>
                <option value="mutuelle">Mutuelle</option>
                <option value="secu">Securite sociale</option>
              </select>
              {errors.payer_type && <p className="mt-1 text-xs text-danger">{errors.payer_type.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Intervalle (jours)</label>
              <input
                type="number"
                min="1"
                {...register("interval_days", { valueAsNumber: true })}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              {errors.interval_days && <p className="mt-1 text-xs text-danger">{errors.interval_days.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Jours retard min.</label>
              <input
                type="number"
                min="0"
                value={minDays}
                onChange={(e) => setMinDays(Number(e.target.value))}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Montant min. (EUR)</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={minAmount}
                onChange={(e) => setMinAmount(Number(e.target.value))}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Max relances</label>
              <input
                type="number"
                min="1"
                value={maxReminders}
                onChange={(e) => setMaxReminders(Number(e.target.value))}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={!isValid || isSubmitting}>
              {isSubmitting ? "Creation..." : "Creer le plan"}
            </Button>
            <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
              Annuler
            </Button>
          </div>
        </form>
      )}

      {(plans?.length ?? 0) === 0 ? (
        <EmptyState
          title="Aucun plan"
          description="Creez votre premier plan de relance pour automatiser vos relances."
        />
      ) : (
        <div className="space-y-4">
          {(plans ?? []).map((plan) => {
            let rules: Record<string, number> = {};
            try {
              rules = JSON.parse(plan.rules_json);
            } catch {
              /* empty */
            }
            let channels: string[] = [];
            try {
              channels = JSON.parse(plan.channel_sequence);
            } catch {
              /* empty */
            }

            return (
              <div
                key={plan.id}
                className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-semibold text-text-primary">{plan.name}</h4>
                    <StatusBadge status={plan.payer_type} />
                    {plan.is_active ? (
                      <span className="text-xs text-emerald-700 bg-emerald-50 rounded-full px-2 py-0.5">Actif</span>
                    ) : (
                      <span className="text-xs text-text-secondary bg-gray-100 rounded-full px-2 py-0.5">Inactif</span>
                    )}
                  </div>
                  <p className="text-xs text-text-secondary">
                    Retard min. {rules.min_days_overdue || 7}j | Montant min. {rules.min_amount || 0} EUR | Max{" "}
                    {rules.max_reminders || 3} relances | Intervalle {plan.interval_days}j | Canaux:{" "}
                    {channels.join(" → ")}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    onClick={() => executePlan(plan.id)}
                    disabled={inFlightId !== null}
                    title="Executer maintenant"
                  >
                    <Play className="h-4 w-4" />
                  </Button>
                  <button
                    onClick={() => togglePlan(plan.id, plan.is_active)}
                    disabled={inFlightId !== null}
                    className="rounded-lg p-2 hover:bg-gray-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    title={plan.is_active ? "Desactiver" : "Activer"}
                  >
                    {plan.is_active ? (
                      <ToggleRight className="h-5 w-5 text-emerald-600" />
                    ) : (
                      <ToggleLeft className="h-5 w-5 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
