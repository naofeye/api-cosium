"use client";

import { useState } from "react";
import {
  HelpCircle,
  Keyboard,
  ChevronDown,
  ChevronRight,
  Mail,
  Phone,
  BookOpen,
  RefreshCw,
  Info,
  Shield,
  Cookie,
  FileText,
  Globe,
} from "lucide-react";

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
    question: "Comment fonctionne la synchronisation Cosium ?",
    answer:
      "OptiFlow se connecte a votre ERP Cosium en lecture seule pour recuperer les donnees clients, factures, paiements, ordonnances et rendez-vous. La synchronisation est declenchee depuis la page Administration. Aucune donnee n'est modifiee dans Cosium : la synchronisation est unidirectionnelle (Cosium vers OptiFlow uniquement).",
  },
  {
    question: "Comment preparer une prise en charge (PEC) ?",
    answer:
      "Allez dans Assistance PEC via le menu lateral. Selectionnez un client, puis lancez la preparation. Le systeme consolide automatiquement les donnees depuis toutes les sources (Cosium, documents, devis) et detecte les incoherences. Verifiez chaque champ, corrigez si necessaire, puis soumettez la PEC.",
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
  { keys: "Ctrl + B", description: "Ouvrir/fermer la barre laterale" },
  { keys: "Escape", description: "Fermer la modale ou le panneau actif" },
  { keys: "Alt + D", description: "Aller au Dashboard" },
  { keys: "Alt + C", description: "Aller aux Clients" },
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
  const [cosiumGuideOpen, setCosiumGuideOpen] = useState(false);

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

      {/* Quick links */}
      <section>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <a
            href="#faq"
            className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:border-blue-400 hover:shadow-md transition-all"
          >
            <div className="rounded-lg bg-blue-100 p-2">
              <BookOpen className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Questions frequentes</p>
              <p className="text-xs text-gray-500">{faqItems.length} questions</p>
            </div>
          </a>
          <a
            href="#raccourcis"
            className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:border-blue-400 hover:shadow-md transition-all"
          >
            <div className="rounded-lg bg-purple-100 p-2">
              <Keyboard className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Raccourcis clavier</p>
              <p className="text-xs text-gray-500">{shortcuts.length} raccourcis</p>
            </div>
          </a>
          <a
            href="#cosium-cookie"
            className="flex items-center gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:border-blue-400 hover:shadow-md transition-all"
          >
            <div className="rounded-lg bg-amber-100 p-2">
              <Cookie className="h-5 w-5 text-amber-600" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900">Cookie Cosium</p>
              <p className="text-xs text-gray-500">Guide de renouvellement</p>
            </div>
          </a>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Questions frequentes</h2>
        <div className="space-y-2">
          {faqItems.map((item, index) => (
            <FAQAccordion key={index} item={item} />
          ))}
        </div>
      </section>

      {/* Cosium cookie renewal guide */}
      <section id="cosium-cookie">
        <div className="rounded-xl border border-amber-200 bg-amber-50 shadow-sm overflow-hidden">
          <button
            onClick={() => setCosiumGuideOpen(!cosiumGuideOpen)}
            className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-amber-100/50 transition-colors"
            aria-expanded={cosiumGuideOpen}
          >
            <div className="flex items-center gap-3">
              <Cookie className="h-5 w-5 text-amber-600" />
              <div>
                <h2 className="text-lg font-semibold text-gray-800">Comment renouveler le cookie Cosium</h2>
                <p className="text-sm text-gray-600 mt-0.5">
                  Guide pas a pas pour maintenir la connexion avec votre ERP Cosium
                </p>
              </div>
            </div>
            {cosiumGuideOpen ? (
              <ChevronDown className="h-5 w-5 text-gray-500 shrink-0" />
            ) : (
              <ChevronRight className="h-5 w-5 text-gray-500 shrink-0" />
            )}
          </button>
          {cosiumGuideOpen && (
            <div className="px-6 pb-6 space-y-4">
              <div className="bg-white rounded-lg border border-amber-200 p-4">
                <h3 className="text-sm font-semibold text-gray-800 mb-3">Etapes de renouvellement</h3>
                <ol className="space-y-3 text-sm text-gray-700">
                  <li className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">1</span>
                    <span>Connectez-vous a votre espace Cosium via votre navigateur : <strong>https://c1.cosium.biz/votre-tenant</strong></span>
                  </li>
                  <li className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">2</span>
                    <span>Entrez vos identifiants Cosium (login et mot de passe)</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">3</span>
                    <span>Une fois connecte, allez dans <strong>Administration &gt; Connexion ERP</strong> dans OptiFlow</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">4</span>
                    <span>Cliquez sur <strong>&quot;Tester la connexion&quot;</strong> pour verifier que le cookie est valide</span>
                  </li>
                  <li className="flex gap-3">
                    <span className="shrink-0 flex items-center justify-center h-6 w-6 rounded-full bg-amber-100 text-amber-700 text-xs font-bold">5</span>
                    <span>Si la connexion echoue, cliquez sur <strong>&quot;Rafraichir le token&quot;</strong> pour re-authentifier</span>
                  </li>
                </ol>
              </div>
              <div className="flex items-start gap-2 text-xs text-amber-700">
                <Info className="h-4 w-4 shrink-0 mt-0.5" />
                <p>Le cookie Cosium expire regulierement pour des raisons de securite. Si la synchronisation cesse de fonctionner, c&apos;est probablement que le cookie a expire. Renouvelez-le en suivant les etapes ci-dessus.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Keyboard shortcuts */}
      <section id="raccourcis">
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

      {/* Documentation link */}
      <section>
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="rounded-lg bg-blue-100 p-2">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-800">Documentation</h2>
              <p className="mt-1 text-sm text-gray-600">
                Consultez la documentation complete pour decouvrir toutes les fonctionnalites d&apos;OptiFlow AI.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <a
                  href="https://docs.optiflow.ai"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Globe className="h-4 w-4" aria-hidden="true" />
                  Documentation en ligne
                </a>
                <a
                  href="/api/v1/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Shield className="h-4 w-4" aria-hidden="true" />
                  API Swagger
                </a>
              </div>
            </div>
          </div>
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
            <div className="mt-3 flex flex-wrap gap-3">
              <a
                href="mailto:support@optiflow.ai"
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Mail className="h-4 w-4" aria-hidden="true" />
                support@optiflow.ai
              </a>
              <a
                href="tel:+33123456789"
                className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-blue-200 text-blue-700 text-sm font-medium rounded-lg hover:bg-blue-50 transition-colors"
              >
                <Phone className="h-4 w-4" aria-hidden="true" />
                01 23 45 67 89
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Version info */}
      <section className="text-center pb-4">
        <div className="inline-flex items-center gap-2 text-xs text-gray-400">
          <Info className="h-3.5 w-3.5" aria-hidden="true" />
          <span>OptiFlow AI v1.0.0 | Plateforme metier pour opticiens</span>
        </div>
      </section>
    </div>
  );
}
