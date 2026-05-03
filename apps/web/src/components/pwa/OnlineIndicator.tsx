"use client";

import { useEffect, useState } from "react";
import { CloudOff, Wifi } from "lucide-react";

/**
 * Indicateur statut online/offline en bas a droite (toast persistant
 * visible uniquement quand offline). Utilise navigator.onLine + events
 * online/offline. Best-effort — false-positive possible si reseau ok mais
 * l'API down (auquel cas le toast `api-error` se charge de l'avertir).
 */
export function OnlineIndicator() {
  const [online, setOnline] = useState<boolean>(true);
  const [justReconnected, setJustReconnected] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setOnline(navigator.onLine);

    const handleOnline = () => {
      setOnline(true);
      setJustReconnected(true);
      // Banniere "reconnecte" 4s puis disparait
      setTimeout(() => setJustReconnected(false), 4000);
    };
    const handleOffline = () => {
      setOnline(false);
      setJustReconnected(false);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (online && !justReconnected) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-4 right-4 z-50 max-w-xs"
    >
      {!online ? (
        <div className="flex items-center gap-2 rounded-lg bg-amber-100 border border-amber-300 px-3 py-2 text-sm font-medium text-amber-900 shadow-md">
          <CloudOff size={16} aria-hidden="true" />
          <span>Hors ligne — modifications mises en file d&apos;attente</span>
        </div>
      ) : (
        <div className="flex items-center gap-2 rounded-lg bg-emerald-100 border border-emerald-300 px-3 py-2 text-sm font-medium text-emerald-900 shadow-md">
          <Wifi size={16} aria-hidden="true" />
          <span>Reconnecte</span>
        </div>
      )}
    </div>
  );
}
