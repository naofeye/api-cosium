"use client";

import { useEffect, useState } from "react";
import { Download, X } from "lucide-react";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

const DISMISS_KEY = "optiflow:install-dismissed";
const DISMISS_DURATION_MS = 7 * 24 * 60 * 60 * 1000;

export function InstallPrompt() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      const dismissedAt = localStorage.getItem(DISMISS_KEY);
      if (dismissedAt && Date.now() - Number(dismissedAt) < DISMISS_DURATION_MS) return;
      setDeferred(e as BeforeInstallPromptEvent);
      setVisible(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const install = async () => {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    setVisible(false);
    setDeferred(null);
  };

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setVisible(false);
  };

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-label="Installer l'application"
      className="fixed bottom-20 left-4 right-4 z-50 rounded-xl border border-border bg-white p-4 shadow-lg lg:bottom-4 lg:left-auto lg:right-4 lg:max-w-sm"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-blue-50">
          <Download className="h-5 w-5 text-primary" aria-hidden="true" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-text-primary">Installer OptiFlow</p>
          <p className="mt-0.5 text-xs text-text-secondary">
            Ajoutez l&apos;application a votre ecran d&apos;accueil pour un acces rapide.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={install}
              className="rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-hover"
            >
              Installer
            </button>
            <button
              onClick={dismiss}
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-gray-50"
            >
              Plus tard
            </button>
          </div>
        </div>
        <button
          onClick={dismiss}
          aria-label="Fermer"
          className="flex-none rounded-lg p-1 text-text-secondary hover:bg-gray-50"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
