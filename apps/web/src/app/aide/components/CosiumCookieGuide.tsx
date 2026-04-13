"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Cookie, Info } from "lucide-react";

const STEPS = [
  <>Connectez-vous à votre espace Cosium via votre navigateur : <strong>https://c1.cosium.biz/votre-tenant</strong></>,
  <>Entrez vos identifiants Cosium (login et mot de passe)</>,
  <>Une fois connecté, allez dans <strong>Administration &gt; Connexion ERP</strong> dans OptiFlow</>,
  <>Cliquez sur <strong>&quot;Tester la connexion&quot;</strong> pour vérifier que le cookie est valide</>,
  <>Si la connexion échoue, cliquez sur <strong>&quot;Rafraîchir le token&quot;</strong> pour ré-authentifier</>,
];

export function CosiumCookieGuide() {
  const [open, setOpen] = useState(false);

  return (
    <section id="cosium-cookie">
      <div className="rounded-xl border border-amber-200 bg-amber-50 shadow-sm overflow-hidden">
        <button
          onClick={() => setOpen(!open)}
          className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-amber-100/50 transition-colors"
          aria-expanded={open}
        >
          <div className="flex items-center gap-3">
            <Cookie className="h-5 w-5 text-amber-600" aria-hidden="true" />
            <div>
              <h2 className="text-lg font-semibold text-gray-800">Comment renouveler le cookie Cosium</h2>
              <p className="text-sm text-gray-600 mt-0.5">
                Guide pas à pas pour maintenir la connexion avec votre ERP Cosium
              </p>
            </div>
          </div>
          {open ? (
            <ChevronDown className="h-5 w-5 text-gray-500 shrink-0" aria-hidden="true" />
          ) : (
            <ChevronRight className="h-5 w-5 text-gray-500 shrink-0" aria-hidden="true" />
          )}
        </button>
        {open && (
          <div className="px-6 pb-6 space-y-4">
            <div className="bg-white rounded-lg border border-amber-200 p-4">
              <h3 className="text-sm font-semibold text-gray-800 mb-3">Étapes de renouvellement</h3>
              <ol className="space-y-3 text-sm text-gray-700">
                {STEPS.map((content, i) => (
                  <li key={i} className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">
                      {i + 1}
                    </span>
                    <span>{content}</span>
                  </li>
                ))}
              </ol>
            </div>
            <div className="flex items-start gap-2 text-xs text-amber-700">
              <Info className="h-4 w-4 shrink-0 mt-0.5" aria-hidden="true" />
              <p>
                Le cookie Cosium expire régulièrement pour des raisons de sécurité. Si la synchronisation cesse de fonctionner, c&apos;est probablement que le cookie a expiré. Renouvelez-le en suivant les étapes ci-dessus.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
