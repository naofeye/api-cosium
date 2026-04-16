"use client";

import { useEffect } from "react";

/**
 * Enregistre le service worker `/sw.js` en production uniquement.
 * Desactive en dev pour eviter les caches qui masquent les modifications.
 */
export function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    const url = "/sw.js";
    navigator.serviceWorker.register(url).catch(() => {
      // Silencieux : un echec SW ne doit jamais casser l'app
    });
  }, []);
  return null;
}
