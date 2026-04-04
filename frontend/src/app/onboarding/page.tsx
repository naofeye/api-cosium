"use client";

import { useState } from "react";
import { Check, Building2, Link2, Download, Settings, PartyPopper } from "lucide-react";
import { cn } from "@/lib/utils";
import { StepAccount } from "./steps/StepAccount";
import { StepCosium } from "./steps/StepCosium";
import { StepImport } from "./steps/StepImport";
import { StepPreferences } from "./steps/StepPreferences";
import { StepComplete } from "./steps/StepComplete";

const STEPS = [
  { id: 1, label: "Compte", icon: Building2 },
  { id: 2, label: "Cosium", icon: Link2 },
  { id: 3, label: "Import", icon: Download },
  { id: 4, label: "Preferences", icon: Settings },
  { id: 5, label: "Termine", icon: PartyPopper },
];

function Stepper({ currentStep }: { currentStep: number }) {
  return (
    <nav className="mb-8" aria-label="Progression de l'inscription">
      <ol className="flex items-center justify-center gap-2 sm:gap-4">
        {STEPS.map((step, index) => {
          const isCompleted = currentStep > step.id;
          const isActive = currentStep === step.id;
          const Icon = step.icon;
          return (
            <li key={step.id} className="flex items-center gap-2 sm:gap-4">
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                    isCompleted && "bg-emerald-600 text-white",
                    isActive && "bg-blue-600 text-white",
                    !isCompleted && !isActive && "bg-gray-200 text-gray-500",
                  )}
                >
                  {isCompleted ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium hidden sm:block",
                    isActive && "text-blue-600",
                    isCompleted && "text-emerald-600",
                    !isCompleted && !isActive && "text-gray-400",
                  )}
                >
                  {step.label}
                </span>
              </div>
              {index < STEPS.length - 1 && (
                <div className={cn("h-0.5 w-8 sm:w-12", currentStep > step.id ? "bg-emerald-600" : "bg-gray-200")} />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const goNext = () => setCurrentStep((prev) => Math.min(prev + 1, 5));

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4 py-8">
      <div className="mb-6 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white text-lg font-bold">
          O
        </div>
        <span className="text-xl font-bold text-gray-900">OptiFlow AI</span>
      </div>

      <Stepper currentStep={currentStep} />

      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 shadow-lg">
        {currentStep === 1 && <StepAccount onComplete={goNext} />}
        {currentStep === 2 && <StepCosium onComplete={goNext} onSkip={goNext} />}
        {currentStep === 3 && <StepImport onComplete={goNext} onSkip={goNext} />}
        {currentStep === 4 && <StepPreferences onComplete={goNext} />}
        {currentStep === 5 && <StepComplete />}
      </div>

      <p className="mt-6 text-center text-xs text-gray-400">OptiFlow AI v0.1 — Plateforme metier pour opticiens</p>
    </div>
  );
}
