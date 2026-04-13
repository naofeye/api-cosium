"use client";

import { useState } from "react";
import { ClipboardCheck, Copy } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { ConsolidatedClientProfile } from "@/lib/types/pec-preparation";
import { fieldValue } from "../utils";

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    document.body.removeChild(ta);
  }
}

function SectionCopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await copyText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button
      variant={copied ? "primary" : "ghost"}
      size="sm"
      onClick={handleCopy}
      aria-label={`Copier la section ${label}`}
    >
      {copied ? (
        <><ClipboardCheck className="h-3 w-3 mr-1" aria-hidden="true" /> Copie !</>
      ) : (
        <><Copy className="h-3 w-3 mr-1" aria-hidden="true" /> Copier</>
      )}
    </Button>
  );
}

function buildSections(profile: ConsolidatedClientProfile) {
  return [
    {
      title: "ASSURE",
      lines: [
        `Nom: ${fieldValue(profile.nom)}`,
        `Prenom: ${fieldValue(profile.prenom)}`,
        `Date de naissance: ${fieldValue(profile.date_naissance)}`,
        `N. Securite sociale: ${fieldValue(profile.numero_secu)}`,
      ],
    },
    {
      title: "MUTUELLE",
      lines: [
        `Organisme: ${fieldValue(profile.mutuelle_nom)}`,
        `N. Adherent: ${fieldValue(profile.mutuelle_numero_adherent)}`,
        `Code AMC: ${fieldValue(profile.mutuelle_code_organisme)}`,
      ],
    },
    {
      title: "PRESCRIPTEUR",
      lines: [
        `${fieldValue(profile.prescripteur)}`,
        `Date ordonnance: ${fieldValue(profile.date_ordonnance)}`,
      ],
    },
    {
      title: "CORRECTION",
      lines: [
        `OD: Sph ${fieldValue(profile.sphere_od)}  Cyl ${fieldValue(profile.cylinder_od)}  Axe ${fieldValue(profile.axis_od)}  Add ${fieldValue(profile.addition_od)}`,
        `OG: Sph ${fieldValue(profile.sphere_og)}  Cyl ${fieldValue(profile.cylinder_og)}  Axe ${fieldValue(profile.axis_og)}  Add ${fieldValue(profile.addition_og)}`,
        `EP: ${fieldValue(profile.ecart_pupillaire)}`,
      ],
    },
    {
      title: "EQUIPEMENT",
      lines: [
        ...(profile.monture ? [`Monture: ${fieldValue(profile.monture)}`] : []),
        ...(profile.verres ?? []).map((v, i) => `Verre ${i === 0 ? "OD" : "OG"}: ${fieldValue(v)}`),
      ],
    },
    {
      title: "MONTANTS",
      lines: [
        `Total TTC: ${fieldValue(profile.montant_ttc)} EUR`,
        `Part Securite sociale: ${fieldValue(profile.part_secu)} EUR`,
        `Part Mutuelle: ${fieldValue(profile.part_mutuelle)} EUR`,
        `Reste a charge: ${fieldValue(profile.reste_a_charge)} EUR`,
      ],
    },
  ];
}

export function CopyPasteSummary({ profile }: { profile: ConsolidatedClientProfile }) {
  const [allCopied, setAllCopied] = useState(false);
  const sections = buildSections(profile);
  const fullText = sections.map((s) => `=== ${s.title} ===\n${s.lines.join("\n")}`).join("\n\n");

  const handleCopyAll = async () => {
    await copyText(fullText);
    setAllCopied(true);
    setTimeout(() => setAllCopied(false), 2000);
  };

  return (
    <div className="mt-6 rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <ClipboardCheck className="h-5 w-5 text-blue-600" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-gray-900">Resume pour copier-coller</h3>
          <span className="text-xs text-gray-500">(pour saisie portail OCAM)</span>
        </div>
        <Button
          variant={allCopied ? "primary" : "outline"}
          size="sm"
          onClick={handleCopyAll}
        >
          {allCopied ? (
            <><ClipboardCheck className="h-4 w-4 mr-1" aria-hidden="true" /> Copie !</>
          ) : (
            <><Copy className="h-4 w-4 mr-1" aria-hidden="true" /> Copier tout</>
          )}
        </Button>
      </div>
      <div className="divide-y divide-gray-100">
        {sections.map((section) => {
          const sectionText = `=== ${section.title} ===\n${section.lines.join("\n")}`;
          return (
            <div key={section.title} className="px-4 py-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  {section.title}
                </span>
                <SectionCopyButton text={sectionText} label={section.title} />
              </div>
              <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap">
                {section.lines.join("\n")}
              </pre>
            </div>
          );
        })}
      </div>
    </div>
  );
}
