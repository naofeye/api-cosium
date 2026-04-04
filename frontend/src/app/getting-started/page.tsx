"use client";

import { useRouter } from "next/navigation";
import useSWR from "swr";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { CheckCircle, Circle, Building2, Link2, Download, Settings, ArrowRight, LayoutDashboard } from "lucide-react";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface OnboardingStep {
  key: string;
  label: string;
  completed: boolean;
}

interface OnboardingStatus {
  steps: OnboardingStep[];
  current_step: string;
  cosium_connected: boolean;
  first_sync_done: boolean;
  trial_days_remaining: number;
}

/* ------------------------------------------------------------------ */
/*  Step icon mapping                                                  */
/* ------------------------------------------------------------------ */

const STEP_ICONS: Record<string, typeof Building2> = {
  signup: Building2,
  connect_cosium: Link2,
  first_sync: Download,
  preferences: Settings,
};

const STEP_ACTIONS: Record<string, { label: string; href: string }> = {
  connect_cosium: { label: "Connecter Cosium", href: "/onboarding" },
  first_sync: { label: "Lancer l'importation", href: "/onboarding" },
  preferences: { label: "Configurer", href: "/onboarding" },
};

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default function GettingStartedPage() {
  const router = useRouter();
  const { data: status, error, isLoading, mutate } = useSWR<OnboardingStatus>("/onboarding/status");

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <LoadingState text="Chargement de votre progression..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <ErrorState message={error?.message ?? "Impossible de charger le statut"} onRetry={() => mutate()} />
      </div>
    );
  }

  if (!status) return null;

  const completedCount = status.steps.filter((s) => s.completed).length;
  const totalSteps = status.steps.length;
  const allDone = completedCount === totalSteps;
  const progressPercent = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0;

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-8">
      <div className="mx-auto max-w-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Premiers pas</h1>
          <p className="mt-1 text-sm text-gray-500">Completez ces etapes pour profiter pleinement d&apos;OptiFlow.</p>
        </div>

        {/* Trial banner */}
        {status.trial_days_remaining > 0 && (
          <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-center text-sm text-amber-700">
            Periode d&apos;essai — <strong>{status.trial_days_remaining} jours restants</strong>
          </div>
        )}

        {/* Progress bar */}
        <div className="mb-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progression</span>
            <span className="text-sm font-semibold text-blue-600">
              {completedCount} / {totalSteps} etapes
            </span>
          </div>
          <div className="h-2.5 w-full rounded-full bg-gray-100 overflow-hidden">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                allDone ? "bg-emerald-500" : "bg-blue-500",
              )}
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        </div>

        {/* Steps checklist */}
        <div className="space-y-3">
          {status.steps.map((step) => {
            const Icon = STEP_ICONS[step.key] || Circle;
            const action = STEP_ACTIONS[step.key];

            return (
              <div
                key={step.key}
                className={cn(
                  "flex items-center gap-4 rounded-xl border p-4 transition-colors",
                  step.completed ? "border-emerald-200 bg-emerald-50" : "border-gray-200 bg-white",
                )}
              >
                <div
                  className={cn(
                    "flex h-10 w-10 shrink-0 items-center justify-center rounded-full",
                    step.completed ? "bg-emerald-100" : "bg-gray-100",
                  )}
                >
                  {step.completed ? (
                    <CheckCircle className="h-5 w-5 text-emerald-600" />
                  ) : (
                    <Icon className="h-5 w-5 text-gray-400" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className={cn("text-sm font-medium", step.completed ? "text-emerald-700" : "text-gray-900")}>
                    {step.label}
                  </p>
                  {step.completed && <p className="text-xs text-emerald-500">Termine</p>}
                </div>

                {!step.completed && action && (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.push(action.href)}
                    className="shrink-0 text-xs"
                  >
                    {action.label}
                    <ArrowRight className="ml-1 h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            );
          })}
        </div>

        {/* Dashboard link */}
        <div className="mt-8 text-center">
          <Button
            type="button"
            variant={allDone ? "primary" : "outline"}
            onClick={() => router.push("/dashboard")}
            className="mx-auto"
          >
            <LayoutDashboard className="mr-2 h-4 w-4" />
            Acceder au tableau de bord
          </Button>
        </div>
      </div>
    </div>
  );
}
