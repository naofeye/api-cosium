import { Check } from "lucide-react";

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}

export interface Step {
  id: string;
  label: string;
  description?: string;
}

interface Props {
  steps: Step[];
  current: string;       // step.id de l'etape active
}

export function Stepper({ steps, current }: Props) {
  const currentIdx = steps.findIndex((s) => s.id === current);

  return (
    <nav aria-label="Progression" className="mb-6">
      <ol className="flex items-center w-full">
        {steps.map((step, i) => {
          const isCompleted = i < currentIdx;
          const isCurrent = i === currentIdx;
          const isLast = i === steps.length - 1;
          return (
            <li
              key={step.id}
              className={cn("flex items-center", !isLast && "flex-1")}
              aria-current={isCurrent ? "step" : undefined}
            >
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold transition-colors",
                    isCompleted && "bg-emerald-500 text-white",
                    isCurrent && "bg-blue-600 text-white ring-4 ring-blue-200",
                    !isCompleted && !isCurrent && "bg-gray-200 text-gray-500",
                  )}
                >
                  {isCompleted ? <Check className="h-4 w-4" aria-hidden="true" /> : i + 1}
                </div>
                <div className="text-center">
                  <div className={cn(
                    "text-xs font-semibold",
                    isCurrent ? "text-blue-700" : isCompleted ? "text-emerald-700" : "text-gray-500",
                  )}>
                    {step.label}
                  </div>
                  {step.description && (
                    <div className="text-[10px] text-gray-400 hidden sm:block">{step.description}</div>
                  )}
                </div>
              </div>
              {!isLast && (
                <div
                  className={cn(
                    "h-0.5 flex-1 mx-2 transition-colors",
                    isCompleted ? "bg-emerald-500" : "bg-gray-200",
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
