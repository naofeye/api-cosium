"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

const MODULE_LABELS = {
  crm: { label: "CRM / Dossiers clients", description: "Gestion centralisee de vos clients" },
  devis: { label: "Devis", description: "Creation et suivi de devis" },
  facturation: { label: "Facturation", description: "Factures et encaissements" },
  pec: { label: "Tiers payant / PEC", description: "Prises en charge mutuelles et secu" },
  marketing: { label: "Marketing", description: "Campagnes email et SMS" },
  rapprochement: { label: "Rapprochement bancaire", description: "Correspondance paiements / releves" },
} as const;

type ModuleKey = keyof typeof MODULE_LABELS;

export function StepPreferences({ onComplete }: { onComplete: () => void }) {
  const [timezone, setTimezone] = useState("Europe/Paris");
  const [modules, setModules] = useState<Record<ModuleKey, boolean>>({
    crm: true,
    devis: true,
    facturation: true,
    pec: false,
    marketing: false,
    rapprochement: false,
  });

  const toggleModule = (key: ModuleKey) => setModules((prev) => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="space-y-5">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-gray-900">Configurer vos preferences</h2>
        <p className="mt-1 text-sm text-gray-500">Choisissez les modules a activer. Modifiable plus tard.</p>
      </div>
      <div>
        <label htmlFor="timezone" className="mb-1.5 block text-sm font-medium text-gray-700">
          Fuseau horaire
        </label>
        <select
          id="timezone"
          value={timezone}
          onChange={(e) => setTimezone(e.target.value)}
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        >
          <option value="Europe/Paris">Europe/Paris (UTC+1)</option>
          <option value="Europe/Brussels">Europe/Bruxelles (UTC+1)</option>
          <option value="Europe/Zurich">Europe/Zurich (UTC+1)</option>
          <option value="America/Guadeloupe">Guadeloupe (UTC-4)</option>
          <option value="Indian/Reunion">La Reunion (UTC+4)</option>
        </select>
      </div>
      <div>
        <p className="mb-3 text-sm font-medium text-gray-700">Modules actifs</p>
        <div className="space-y-2">
          {(Object.keys(MODULE_LABELS) as ModuleKey[]).map((key) => (
            <label
              key={key}
              className={cn(
                "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                modules[key] ? "border-blue-300 bg-blue-50" : "border-gray-200 bg-white hover:bg-gray-50",
              )}
            >
              <input
                type="checkbox"
                checked={modules[key]}
                onChange={() => toggleModule(key)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <span className="text-sm font-medium text-gray-900">{MODULE_LABELS[key].label}</span>
                <p className="text-xs text-gray-500">{MODULE_LABELS[key].description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>
      <Button type="button" onClick={onComplete} className="w-full">
        Continuer
      </Button>
    </div>
  );
}
