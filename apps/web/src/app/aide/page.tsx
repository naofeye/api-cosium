"use client";

import { HelpCircle, Info } from "lucide-react";

import { CosiumCookieGuide } from "./components/CosiumCookieGuide";
import { DocumentationLinks, SupportContact } from "./components/HelpContact";
import { FAQAccordion } from "./components/FAQAccordion";
import { HelpQuickLinks } from "./components/HelpQuickLinks";
import { ShortcutsTable } from "./components/ShortcutsTable";
import { faqItems, shortcuts } from "./data";

export default function AidePage() {
  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <nav className="text-sm text-gray-500 mb-2" aria-label="Breadcrumb">
          <span>Accueil</span>
          <span className="mx-2">/</span>
          <span className="text-gray-900">Aide</span>
        </nav>
        <div className="flex items-center gap-3">
          <HelpCircle className="h-7 w-7 text-blue-600" aria-hidden="true" />
          <h1 className="text-2xl font-bold text-gray-900">Centre d&apos;aide</h1>
        </div>
        <p className="mt-2 text-sm text-gray-500">
          Trouvez rapidement des réponses à vos questions sur OptiFlow AI.
        </p>
      </div>

      <HelpQuickLinks faqCount={faqItems.length} shortcutsCount={shortcuts.length} />

      <section id="faq">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Questions fréquentes</h2>
        <div className="space-y-2">
          {faqItems.map((item, index) => (
            <FAQAccordion key={index} item={item} />
          ))}
        </div>
      </section>

      <CosiumCookieGuide />

      <ShortcutsTable shortcuts={shortcuts} />

      <DocumentationLinks />

      <SupportContact />

      <section className="text-center pb-4">
        <div className="inline-flex items-center gap-2 text-xs text-gray-400">
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          <span>OptiFlow AI v1.0.0 | Plateforme metier pour opticiens</span>
        </div>
      </section>
    </div>
  );
}
