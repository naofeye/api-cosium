"use client";

import { useEffect, useState } from "react";
import { Download, X, Smartphone, Share } from "lucide-react";

/**
 * Banniere "Installer l'application" pour PWA.
 *
 * Comportement :
 * - Android/Chrome/Edge : intercepte l'evenement `beforeinstallprompt` et
 *   affiche un bouton qui declenche l'installation native.
 * - iOS Safari : affiche les instructions manuelles (Partager > Sur l'ecran
 *   d'accueil) car Safari ne supporte pas l'API d'installation programmatique.
 * - Si deja installe (mode standalone) : ne s'affiche pas.
 * - Si l'utilisateur a ferme la banniere (X) : memorise dans localStorage
 *   et ne reaffiche pas avant 7 jours.
 */

const DISMISS_KEY = "optiflow-install-prompt-dismissed";
const REMIND_AFTER_DAYS = 7;

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
  prompt(): Promise<void>;
}

function isStandalone(): boolean {
  if (typeof window === "undefined") return false;
  // iOS Safari : navigator.standalone non standard
  // Android/Chrome : matchMedia display-mode
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const navAny = window.navigator as any;
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    navAny.standalone === true
  );
}

function isIOS(): boolean {
  if (typeof window === "undefined") return false;
  return /iPad|iPhone|iPod/.test(window.navigator.userAgent);
}

function wasRecentlyDismissed(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const ts = window.localStorage.getItem(DISMISS_KEY);
    if (!ts) return false;
    const elapsed = Date.now() - parseInt(ts, 10);
    return elapsed < REMIND_AFTER_DAYS * 24 * 60 * 60 * 1000;
  } catch {
    return false;
  }
}

export function InstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);
  const [showIosBanner, setShowIosBanner] = useState(false);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (isStandalone()) return; // deja installe
    if (wasRecentlyDismissed()) {
      setDismissed(true);
      return;
    }

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // iOS : aucune API d'installation, on affiche les instructions
    if (isIOS()) {
      setShowIosBanner(true);
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  if (dismissed || isStandalone()) return null;
  if (!deferredPrompt && !showIosBanner) return null;

  const handleDismiss = () => {
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch {
      // localStorage indisponible (mode prive iOS) — pas grave
    }
    setDismissed(true);
  };

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const result = await deferredPrompt.userChoice;
    if (result.outcome === "accepted") {
      setDismissed(true);
    }
    setDeferredPrompt(null);
  };

  return (
    <div
      role="dialog"
      aria-label="Installer OptiFlow"
      className="fixed bottom-4 left-4 right-4 z-50 max-w-sm rounded-xl border border-border bg-bg-card shadow-2xl ring-1 ring-black/5 lg:left-auto lg:right-6 lg:bottom-6"
    >
      <div className="flex items-start gap-3 p-4">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-blue-50 text-blue-600">
          <Smartphone className="h-5 w-5" aria-hidden="true" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-text-primary">
            Installer OptiFlow sur votre telephone
          </p>
          {deferredPrompt ? (
            <p className="mt-0.5 text-xs text-text-secondary">
              Acces rapide depuis l&apos;ecran d&apos;accueil, mode plein ecran,
              fonctionne hors ligne.
            </p>
          ) : (
            <div className="mt-1 text-xs text-text-secondary space-y-0.5">
              <p>Sur iPhone/iPad :</p>
              <p className="flex items-center gap-1">
                1. Touchez{" "}
                <Share className="h-3.5 w-3.5 inline" aria-hidden="true" />
                <span className="font-medium">Partager</span>
              </p>
              <p>2. &quot;Sur l&apos;ecran d&apos;accueil&quot;</p>
            </div>
          )}
          <div className="mt-3 flex items-center gap-2">
            {deferredPrompt && (
              <button
                onClick={handleInstall}
                className="inline-flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <Download className="h-3.5 w-3.5" aria-hidden="true" />
                Installer
              </button>
            )}
            <button
              onClick={handleDismiss}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-gray-100"
            >
              Plus tard
            </button>
          </div>
        </div>
        <button
          onClick={handleDismiss}
          className="flex-none rounded p-1 text-text-secondary hover:bg-gray-100"
          aria-label="Fermer la banniere d'installation"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
