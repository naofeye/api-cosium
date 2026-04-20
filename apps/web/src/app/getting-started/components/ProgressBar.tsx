import { cn } from "@/lib/utils";
import {
  Check,
  Sparkles,
  Link2,
  RefreshCw,
  Database,
  Rocket,
} from "lucide-react";

export const STEP_DEFS = [
  { id: 1, label: "Bienvenue", icon: Sparkles },
  { id: 2, label: "Connexion Cosium", icon: Link2 },
  { id: 3, label: "Synchronisation", icon: RefreshCw },
  { id: 4, label: "Verification", icon: Database },
  { id: 5, label: "C'est parti !", icon: Rocket },
] as const;

export function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = ((current - 1) / (total - 1)) * 100;
  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      <div className="flex items-center justify-between mb-2">
        {STEP_DEFS.map((step) => {
          const isCompleted = current > step.id;
          const isActive = current === step.id;
          const Icon = step.icon;
          return (
            <div key={step.id} className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                  isCompleted && "bg-emerald-600 text-white",
                  isActive && "bg-blue-600 text-white",
                  !isCompleted && !isActive && "bg-gray-200 text-gray-500"
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs font-medium hidden sm:block",
                  isActive && "text-blue-600",
                  isCompleted && "text-emerald-600",
                  !isCompleted && !isActive && "text-gray-400"
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-blue-600 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-center text-xs text-gray-500">
        Etape {current} sur {total}
      </p>
    </div>
  );
}
