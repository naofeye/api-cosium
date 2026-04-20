"use client";

import { useEffect, useState, useCallback } from "react";
import { RefreshCw, X } from "lucide-react";

/**
 * Enregistre le service worker `/sw.js` et notifie l'utilisateur
 * quand une nouvelle version est disponible.
 */
export function ServiceWorkerRegister() {
  const [showUpdate, setShowUpdate] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(
    null,
  );

  const applyUpdate = useCallback(() => {
    if (waitingWorker) {
      waitingWorker.postMessage({ type: "SKIP_WAITING" });
    }
    setShowUpdate(false);
    // Recharger la page apres que le nouveau SW a pris le controle
    window.location.reload();
  }, [waitingWorker]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (!("serviceWorker" in navigator)) return;

    const registerSW = async () => {
      try {
        const registration = await navigator.serviceWorker.register("/sw.js");

        // Verifier si un SW en attente existe deja (ex: onglet rouvert)
        if (registration.waiting) {
          setWaitingWorker(registration.waiting);
          setShowUpdate(true);
        }

        // Ecouter les nouvelles installations
        registration.addEventListener("updatefound", () => {
          const newWorker = registration.installing;
          if (!newWorker) return;

          newWorker.addEventListener("statechange", () => {
            // Le nouveau SW est installe et en attente d'activation
            if (
              newWorker.state === "installed" &&
              navigator.serviceWorker.controller
            ) {
              setWaitingWorker(newWorker);
              setShowUpdate(true);
            }
          });
        });

        // Quand le controleur change (apres skipWaiting), recharger
        let refreshing = false;
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          if (!refreshing) {
            refreshing = true;
            window.location.reload();
          }
        });
      } catch {
        // Silencieux : un echec SW ne doit jamais casser l'app
      }
    };

    registerSW();
  }, []);

  if (!showUpdate) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed bottom-4 left-4 right-4 z-50 rounded-xl border border-blue-200 bg-blue-50 p-4 shadow-lg sm:left-auto sm:right-4 sm:max-w-sm"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 flex-none items-center justify-center rounded-lg bg-blue-100">
          <RefreshCw
            className="h-4 w-4 text-blue-600"
            aria-hidden="true"
          />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-gray-900">
            Mise a jour disponible
          </p>
          <p className="mt-0.5 text-xs text-gray-600">
            Une nouvelle version d&apos;OptiFlow est prete.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={applyUpdate}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
            >
              Mettre a jour
            </button>
            <button
              onClick={() => setShowUpdate(false)}
              className="rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1"
            >
              Plus tard
            </button>
          </div>
        </div>
        <button
          onClick={() => setShowUpdate(false)}
          aria-label="Fermer la notification de mise a jour"
          className="flex-none rounded-lg p-1 text-gray-400 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}
