"use client";

import { Button } from "@/components/ui/Button";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import { Check, CreditCard, Sparkles, Building2, Cpu } from "lucide-react";

export interface PlanDef {
  id: string;
  name: string;
  price: number;
  icon: typeof CreditCard;
  features: string[];
  highlight?: boolean;
}

export const PLANS: PlanDef[] = [
  {
    id: "solo",
    name: "Solo",
    price: 29,
    icon: Sparkles,
    features: ["1 magasin", "CRM clients", "Gestion documentaire", "Devis & factures", "Support email"],
  },
  {
    id: "reseau",
    name: "Réseau",
    price: 79,
    icon: Building2,
    highlight: true,
    features: [
      "Jusqu'à 10 magasins",
      "Tout Solo +",
      "Multi-tenant",
      "Rapprochement bancaire",
      "Relances automatiques",
      "Support prioritaire",
    ],
  },
  {
    id: "ia_pro",
    name: "IA Pro",
    price: 149,
    icon: Cpu,
    features: [
      "Magasins illimités",
      "Tout Réseau +",
      "Assistants IA",
      "Marketing IA",
      "Analyse prédictive",
      "Support dédié",
    ],
  },
];

export interface PlanSelectorProps {
  currentPlanId: string;
  currentStatus: string;
  checkoutLoading: string | null;
  onCheckout: (planId: string) => void;
}

export function PlanSelector({ currentPlanId, currentStatus, checkoutLoading, onCheckout }: PlanSelectorProps) {
  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-800">Changer de plan</h2>
      <p className="mt-1 text-sm text-text-secondary">Choisissez la formule adaptée à votre activité.</p>

      <div className="mt-6 grid gap-6 sm:grid-cols-3">
        {PLANS.map((plan) => {
          const isCurrent = currentPlanId === plan.id && currentStatus !== "canceled";
          const Icon = plan.icon;
          return (
            <div
              key={plan.id}
              className={cn(
                "flex flex-col rounded-xl border p-6 shadow-sm transition-shadow hover:shadow-md",
                plan.highlight ? "border-primary ring-2 ring-primary/20" : "border-border",
                isCurrent && "bg-blue-50/50",
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "rounded-lg p-2",
                    plan.highlight ? "bg-blue-100 text-primary" : "bg-gray-100 text-gray-600",
                  )}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">{plan.name}</h3>
                  {plan.highlight && <span className="text-xs font-medium text-primary">Populaire</span>}
                </div>
              </div>

              <p className="mt-4 text-3xl font-bold tabular-nums text-gray-900">
                {formatMoney(plan.price)}
                <span className="text-sm font-normal text-text-secondary">/mois</span>
              </p>

              <ul className="mt-6 flex-1 space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                    {f}
                  </li>
                ))}
              </ul>

              <div className="mt-6">
                {isCurrent ? (
                  <Button variant="outline" disabled className="w-full">
                    Plan actuel
                  </Button>
                ) : (
                  <Button
                    variant={plan.highlight ? "primary" : "outline"}
                    className="w-full"
                    loading={checkoutLoading === plan.id}
                    onClick={() => onCheckout(plan.id)}
                  >
                    Choisir ce plan
                  </Button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
