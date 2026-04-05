"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  RefreshCw,
  Users,
  FolderOpen,
  FileText,
  Calendar,
  X,
  ChevronRight,
  Sparkles,
} from "lucide-react";

const STORAGE_KEY = "optiflow_onboarding_done";

interface OnboardingStep {
  icon: React.ReactNode;
  title: string;
  description: string;
  href: string;
}

const STEPS: OnboardingStep[] = [
  {
    icon: <RefreshCw className="h-5 w-5 text-blue-600" />,
    title: "Synchronisez vos donnees Cosium",
    description:
      "Connectez votre ERP Cosium pour importer automatiquement vos clients, factures et rendez-vous.",
    href: "/admin",
  },
  {
    icon: <Users className="h-5 w-5 text-emerald-600" />,
    title: "Consultez vos clients",
    description:
      "Retrouvez toutes les fiches clients avec historique, prescriptions et documents associes.",
    href: "/clients",
  },
  {
    icon: <FolderOpen className="h-5 w-5 text-amber-600" />,
    title: "Gerez vos dossiers",
    description:
      "Creez et suivez vos dossiers clients de bout en bout : devis, factures, PEC et paiements.",
    href: "/cases",
  },
  {
    icon: <FileText className="h-5 w-5 text-purple-600" />,
    title: "Suivez vos factures",
    description:
      "Visualisez toutes vos factures Cosium, suivez les encaissements et les soldes restants.",
    href: "/cosium-factures",
  },
  {
    icon: <Calendar className="h-5 w-5 text-sky-600" />,
    title: "Explorez l'agenda",
    description:
      "Consultez vos rendez-vous synchronises depuis Cosium avec vue jour, semaine et mois.",
    href: "/agenda",
  },
];

export function OnboardingGuide() {
  const [visible, setVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  };

  const step = STEPS[currentStep];

  return (
    <div className="mb-6 rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-white shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 pt-5 pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-blue-600" />
          <h3 className="text-lg font-semibold text-gray-900">
            Bienvenue sur OptiFlow !
          </h3>
          <span className="text-sm text-gray-500">
            Voici comment demarrer :
          </span>
        </div>
        <button
          onClick={handleDismiss}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          aria-label="Fermer le guide"
          title="Ne plus afficher"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress bar */}
      <div className="px-6 pb-2">
        <div className="flex items-center gap-1.5">
          {STEPS.map((_, idx) => (
            <button
              key={idx}
              onClick={() => setCurrentStep(idx)}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                idx === currentStep
                  ? "bg-blue-600"
                  : idx < currentStep
                    ? "bg-blue-300"
                    : "bg-gray-200"
              }`}
              aria-label={`Etape ${idx + 1} sur ${STEPS.length}`}
            />
          ))}
        </div>
        <p className="mt-1 text-xs text-gray-400">
          Etape {currentStep + 1} sur {STEPS.length}
        </p>
      </div>

      {/* Step content */}
      <div className="px-6 pb-5">
        <div className="flex items-start gap-4 rounded-lg bg-white border border-gray-100 p-4">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-50">
            {step.icon}
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-900">
              {step.title}
            </h4>
            <p className="mt-1 text-sm text-gray-500">{step.description}</p>
          </div>
          <Link
            href={step.href}
            className="shrink-0 inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Voir
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        {/* Navigation */}
        <div className="mt-3 flex items-center justify-between">
          <button
            onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
            disabled={currentStep === 0}
            className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Precedent
          </button>
          <div className="flex items-center gap-3">
            <button
              onClick={handleDismiss}
              className="text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              Ne plus afficher
            </button>
            {currentStep < STEPS.length - 1 ? (
              <button
                onClick={() =>
                  setCurrentStep((s) => Math.min(STEPS.length - 1, s + 1))
                }
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 transition-colors"
              >
                Suivant
                <ChevronRight className="h-3.5 w-3.5" />
              </button>
            ) : (
              <button
                onClick={handleDismiss}
                className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700 transition-colors"
              >
                Terminer
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
