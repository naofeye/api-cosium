"use client";

import { Button } from "@/components/ui/Button";
import { Sparkles, CheckCircle, ArrowRight } from "lucide-react";

export function StepBienvenue({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center space-y-6">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-blue-100">
        <Sparkles className="h-10 w-10 text-blue-600" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900">
        Bienvenue sur OptiFlow AI
      </h2>
      <div className="max-w-md mx-auto space-y-3 text-sm text-gray-600 text-left">
        <p>
          OptiFlow AI est votre plateforme metier tout-en-un pour la gestion de
          votre magasin d&apos;optique :
        </p>
        <ul className="space-y-2">
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>CRM client</strong> : fiches 360, historique, prescriptions
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Gestion documentaire</strong> : devis, factures,
              ordonnances
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Tiers payant</strong> : preparation PEC, suivi mutuelles
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Synchronisation Cosium</strong> : import automatique de vos
              donnees ERP
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Assistants IA</strong> : aide a la decision, relances
              intelligentes
            </span>
          </li>
        </ul>
        <p className="text-gray-500 pt-2">
          Ce guide va vous accompagner pour configurer votre espace en quelques
          minutes.
        </p>
      </div>
      <Button onClick={onNext} className="mx-auto">
        Commencer la configuration
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}
