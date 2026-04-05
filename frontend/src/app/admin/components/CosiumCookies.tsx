"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { Key, Save } from "lucide-react";

export function CosiumCookies() {
  const [cookieAccessToken, setCookieAccessToken] = useState("");
  const [cookieDeviceCredential, setCookieDeviceCredential] = useState("");
  const [cookieSaving, setCookieSaving] = useState(false);
  const [cookieMessage, setCookieMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const saveCosiumCookies = async () => {
    if (!cookieAccessToken.trim() || !cookieDeviceCredential.trim()) {
      setCookieMessage({ type: "error", text: "Les deux champs sont obligatoires." });
      return;
    }
    setCookieSaving(true);
    setCookieMessage(null);
    try {
      const res = await fetchJson<{ status: string; message: string }>("/admin/cosium-cookies", {
        method: "POST",
        body: JSON.stringify({
          access_token: cookieAccessToken.trim(),
          device_credential: cookieDeviceCredential.trim(),
        }),
      });
      setCookieMessage({ type: "success", text: res.message || "Cookies enregistres." });
      setCookieAccessToken("");
      setCookieDeviceCredential("");
    } catch {
      setCookieMessage({ type: "error", text: "Erreur lors de l'enregistrement des cookies." });
    } finally {
      setCookieSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Key className="h-5 w-5" /> Acces Cosium — Cookies navigateur
      </h3>
      <p className="text-sm text-text-secondary mb-4">
        Pour renouveler l&apos;acces, connectez-vous sur Cosium dans votre navigateur, puis copiez les cookies{" "}
        <code className="bg-gray-100 px-1 rounded text-xs">access_token</code> et{" "}
        <code className="bg-gray-100 px-1 rounded text-xs">device-credential</code> depuis les DevTools (onglet
        Application &gt; Cookies).
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="text-sm font-medium text-text-primary block mb-1">Cookie access_token</label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Collez le cookie access_token ici..."
            value={cookieAccessToken}
            onChange={(e) => setCookieAccessToken(e.target.value)}
          />
        </div>
        <div>
          <label className="text-sm font-medium text-text-primary block mb-1">Cookie device-credential</label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Collez le cookie device-credential ici..."
            value={cookieDeviceCredential}
            onChange={(e) => setCookieDeviceCredential(e.target.value)}
          />
        </div>
      </div>
      {cookieMessage && (
        <p className={`text-sm mb-3 ${cookieMessage.type === "success" ? "text-emerald-600" : "text-red-600"}`}>
          {cookieMessage.text}
        </p>
      )}
      <Button onClick={saveCosiumCookies} disabled={cookieSaving}>
        <Save className="h-4 w-4 mr-1.5" />
        {cookieSaving ? "Enregistrement..." : "Enregistrer les cookies"}
      </Button>
    </div>
  );
}
