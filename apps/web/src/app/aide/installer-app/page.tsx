"use client";

import { Smartphone, Share, Plus, Apple, Download } from "lucide-react";
import { PageLayout } from "@/components/layout/PageLayout";

export default function InstallerAppPage() {
  return (
    <PageLayout
      title="Installer OptiFlow sur votre telephone"
      description="OptiFlow est une PWA : installez-la comme une vraie application avec un icone sur l'ecran d'accueil."
      breadcrumb={[
        { label: "Aide", href: "/aide" },
        { label: "Installer l'app" },
      ]}
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* iOS */}
        <section className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Apple className="h-5 w-5 text-text-secondary" />
            <h2 className="text-lg font-semibold text-text-primary">
              Sur iPhone / iPad (iOS / iPadOS)
            </h2>
          </div>
          <ol className="space-y-4 text-sm text-text-primary">
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                1
              </span>
              <div>
                <p className="font-medium">Ouvrez OptiFlow dans <strong>Safari</strong></p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Important : l&apos;installation ne fonctionne qu&apos;avec
                  Safari, pas Chrome ni autre navigateur sur iOS.
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                2
              </span>
              <div>
                <p className="font-medium flex items-center gap-1.5">
                  Touchez l&apos;icone <Share className="h-4 w-4 inline" /> <strong>Partager</strong>
                </p>
                <p className="text-xs text-text-secondary mt-0.5">
                  En bas de l&apos;ecran (carre avec une fleche vers le haut).
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                3
              </span>
              <div>
                <p className="font-medium flex items-center gap-1.5">
                  Selectionnez <Plus className="h-4 w-4 inline" /> <strong>Sur l&apos;ecran d&apos;accueil</strong>
                </p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Faites defiler le menu Partager si necessaire.
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                4
              </span>
              <div>
                <p className="font-medium">Touchez <strong>Ajouter</strong></p>
                <p className="text-xs text-text-secondary mt-0.5">
                  L&apos;icone OptiFlow apparait sur votre ecran d&apos;accueil.
                </p>
              </div>
            </li>
          </ol>
        </section>

        {/* Android */}
        <section className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Smartphone className="h-5 w-5 text-text-secondary" />
            <h2 className="text-lg font-semibold text-text-primary">
              Sur Android (Chrome / Edge / Samsung Internet)
            </h2>
          </div>
          <p className="text-sm text-text-secondary mb-4">
            Une banniere &laquo;&nbsp;Installer OptiFlow&nbsp;&raquo; apparait
            automatiquement en bas de l&apos;ecran. Si elle ne s&apos;affiche
            pas, voici la procedure manuelle :
          </p>
          <ol className="space-y-4 text-sm text-text-primary">
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                1
              </span>
              <div>
                <p className="font-medium">Ouvrez le menu du navigateur</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Les 3 points en haut a droite (Chrome / Edge) ou en bas
                  (Samsung Internet).
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                2
              </span>
              <div>
                <p className="font-medium flex items-center gap-1.5">
                  Selectionnez <Download className="h-4 w-4 inline" /> <strong>Installer l&apos;application</strong>
                </p>
                <p className="text-xs text-text-secondary mt-0.5">
                  Ou &laquo;&nbsp;Ajouter a l&apos;ecran d&apos;accueil&nbsp;&raquo;.
                </p>
              </div>
            </li>
            <li className="flex gap-3">
              <span className="flex-none flex h-6 w-6 items-center justify-center rounded-full bg-blue-100 text-blue-700 text-xs font-bold">
                3
              </span>
              <div>
                <p className="font-medium">Confirmez l&apos;installation</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  L&apos;icone OptiFlow s&apos;ajoute au tiroir d&apos;applications
                  et a l&apos;ecran d&apos;accueil.
                </p>
              </div>
            </li>
          </ol>
        </section>
      </div>

      <section className="mt-6 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-text-primary mb-3">
          Avantages de l&apos;installation
        </h2>
        <ul className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-text-primary">
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Acces direct depuis l&apos;ecran d&apos;accueil</strong> sans passer par le navigateur.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Mode plein ecran</strong> : pas de barre d&apos;adresse,
              comme une vraie app.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Hors ligne partiel</strong> : la navigation et les pages
              deja visitees fonctionnent meme sans reseau.
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Notifications push</strong> (Android uniquement, sur
              autorisation).
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Splash screen</strong> au lancement (logo OptiFlow sur fond bleu).
            </span>
          </li>
          <li className="flex items-start gap-2">
            <span className="mt-1 h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span>
              <strong>Mises a jour automatiques</strong> : pas besoin de
              reinstaller, le service worker met a jour en arriere-plan.
            </span>
          </li>
        </ul>
      </section>

      <section className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
        <h3 className="text-sm font-semibold text-amber-900 mb-1">
          Probleme d&apos;installation ?
        </h3>
        <ul className="text-xs text-amber-800 space-y-1 list-disc list-inside">
          <li>
            Sur iOS : utilisez <strong>Safari</strong> (pas Chrome). L&apos;option
            d&apos;ajout a l&apos;ecran d&apos;accueil est cachee dans les autres
            navigateurs.
          </li>
          <li>
            Sur Android : si la banniere n&apos;apparait pas, vous l&apos;avez
            peut-etre fermee. Elle reapparaitra dans 7 jours, ou utilisez la
            procedure manuelle.
          </li>
          <li>
            L&apos;application est deja installee si vous voyez OptiFlow dans
            votre tiroir d&apos;applications.
          </li>
        </ul>
      </section>
    </PageLayout>
  );
}
