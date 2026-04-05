"use client";

import { useState } from "react";
import { HelpCircle, Keyboard, ChevronDown, ChevronRight, Mail } from "lucide-react";

interface FAQItem {
  question: string;
  answer: string;
}

const faqItems: FAQItem[] = [
  {
    question: "Comment creer un nouveau dossier client ?",
    answer:
      'Rendez-vous dans la section Dossiers via le menu lateral, puis cliquez sur le bouton "Nouveau dossier" en haut a droite. Remplissez les informations du client (nom, prenom, coordonnees) et validez. Le dossier sera automatiquement lie au client dans le CRM.',
  },
  {
    question: "Comment generer un devis ?",
    answer:
      'Depuis un dossier client, allez dans l\'onglet "Devis" et cliquez sur "Nouveau devis". Ajoutez les lignes de produits (montures, verres, options), les remises eventuelles, et le systeme calculera automatiquement les montants HT, TTC et le reste a charge. Vous pouvez ensuite envoyer le devis par email ou le telecharger en PDF.',
  },
  {
    question: "Comment importer des clients depuis un fichier CSV ?",
    answer:
      'Allez dans la section Clients, puis cliquez sur "Importer CSV". Le fichier doit contenir les colonnes : nom, prenom, email, telephone. Un apercu vous sera montre avant l\'import definitif. Les doublons potentiels seront detectes automatiquement.',
  },
  {
    question: "Comment rapprocher les paiements bancaires ?",
    answer:
      "Dans la section Rapprochement, importez votre releve bancaire au format CSV. Le systeme proposera automatiquement des correspondances entre les transactions bancaires et les factures en attente. Vous pouvez valider ou corriger les suggestions, puis glisser-deposer manuellement les transactions non matchees.",
  },
  {
    question: "Qu'est-ce que le copilote IA ?",
    answer:
      "Le copilote IA est un assistant intelligent integre a OptiFlow. Il peut analyser vos dossiers, suggerer des actions commerciales, verifier la completude documentaire, et repondre a vos questions sur les donnees financieres. Accedez-y via l'icone IA dans la barre laterale ou avec le raccourci Ctrl+K.",
  },
  {
    question: "Comment contacter le support ?",
    answer:
      "Pour toute question technique ou demande d'assistance, envoyez un email a support@optiflow.ai. Notre equipe repond sous 24h ouvrables. Pour les urgences (blocage complet), appelez le 01 23 45 67 89.",
  },
];

const shortcuts = [
  { keys: "Ctrl + K", description: "Ouvrir la recherche globale / Copilote IA" },
  { keys: "Ctrl + N", description: "Creer un nouveau dossier" },
  { keys: "Escape", description: "Fermer la modale ou le panneau actif" },
];

function FAQAccordion({ item }: { item: FAQItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border border-gray-200 rounded-lg">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-gray-50 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded-lg"
        aria-expanded={open}
      >
        <span className="text-sm font-medium text-gray-900">{item.question}</span>
        {open ? (
          <ChevronDown className="h-4 w-4 text-gray-500 shrink-0 ml-4" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-500 shrink-0 ml-4" />
        )}
      </button>
      {open && (
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{item.answer}</p>
        </div>
      )}
    </div>
  );
}

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
          <HelpCircle className="h-7 w-7 text-blue-600" />
          <h1 className="text-2xl font-bold text-gray-900">Centre d&apos;aide</h1>
        </div>
        <p className="mt-2 text-sm text-gray-500">Trouvez rapidement des reponses a vos questions sur OptiFlow AI.</p>
      </div>

      {/* FAQ Section */}
      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Questions frequentes</h2>
        <div className="space-y-2">
          {faqItems.map((item, index) => (
            <FAQAccordion key={index} item={item} />
          ))}
        </div>
      </section>

      {/* Keyboard shortcuts */}
      <section>
        <div className="flex items-center gap-2 mb-4">
          <Keyboard className="h-5 w-5 text-gray-600" />
          <h2 className="text-lg font-semibold text-gray-800">Raccourcis clavier</h2>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100">
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Raccourci</th>
                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody>
              {shortcuts.map((shortcut, index) => (
                <tr key={index} className="border-b border-gray-50 last:border-0">
                  <td className="px-6 py-3">
                    <kbd className="px-2 py-1 bg-gray-100 border border-gray-300 rounded text-xs font-mono text-gray-700">
                      {shortcut.keys}
                    </kbd>
                  </td>
                  <td className="px-6 py-3 text-sm text-gray-700">{shortcut.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Contact support */}
      <section className="bg-blue-50 rounded-xl border border-blue-200 p-6">
        <div className="flex items-start gap-4">
          <Mail className="h-6 w-6 text-blue-600 mt-0.5" />
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Besoin d&apos;aide supplementaire ?</h2>
            <p className="mt-1 text-sm text-gray-600">
              Notre equipe support est disponible du lundi au vendredi, de 9h a 18h.
            </p>
            <a
              href="mailto:support@optiflow.ai"
              className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Contacter le support
            </a>
          </div>
        </div>
      </section>
    </div>
  );
}
