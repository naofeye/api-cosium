"use client";

import { useState } from "react";
import useSWR from "swr";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { AlertTriangle, CheckCircle, Key, RefreshCw, Save, ExternalLink } from "lucide-react";

interface ConnectionTest {
  connected: boolean;
  error: string | null;
  tenant: string;
  customers_total: number | null;
}

export function CosiumCookies() {
  const [cookieAccessToken, setCookieAccessToken] = useState("");
  const [cookieDeviceCredential, setCookieDeviceCredential] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Test connexion Cosium automatiquement
  const { data: connTest, isLoading: testing, mutate: retest } = useSWR<ConnectionTest>(
    "/admin/cosium-test",
    { refreshInterval: 0, revalidateOnFocus: false }
  );

  const isExpired = connTest && !connTest.connected;

  const saveCookies = async () => {
    if (!cookieAccessToken.trim()) {
      setMessage({ type: "error", text: "Le cookie access_token est obligatoire." });
      return;
    }
    setSaving(true);
    setMessage(null);
    try {
      // Si device-credential n'est pas fourni, on garde l'ancien (il expire dans 1 an)
      const body: Record<string, string> = {
        access_token: cookieAccessToken.trim(),
        device_credential: cookieDeviceCredential.trim() || "G-GREX-__jHvXwYmd6Zgu-n30A0/3",
      };
      const res = await fetchJson<{ status: string; message: string }>("/admin/cosium-cookies", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setMessage({ type: "success", text: res.message || "Cookie enregistre. Test de connexion..." });
      setCookieAccessToken("");
      setCookieDeviceCredential("");
      // Re-tester la connexion
      setTimeout(() => retest(), 2000);
    } catch {
      setMessage({ type: "error", text: "Erreur lors de l'enregistrement." });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      {/* Bandeau d'alerte si cookie expiré */}
      {isExpired && (
        <div className="mb-4 rounded-lg bg-red-50 border border-red-200 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-red-800">Connexion Cosium perdue</p>
            <p className="text-sm text-red-700 mt-1">
              {connTest.error || "Le cookie d'acces a expire."}
            </p>
            <p className="text-sm text-red-700 mt-2 font-medium">
              Pour retablir la connexion, suivez les 3 etapes ci-dessous.
            </p>
          </div>
        </div>
      )}

      {/* Bandeau de succès si connecté */}
      {connTest?.connected && (
        <div className="mb-4 rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-start gap-3">
          <CheckCircle className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-semibold text-emerald-800">Cosium connecte</p>
            <p className="text-sm text-emerald-700">
              Tenant : {connTest.tenant} — {connTest.customers_total?.toLocaleString("fr-FR")} clients accessibles
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => retest()} className="ml-auto shrink-0">
            <RefreshCw className={`h-4 w-4 ${testing ? "animate-spin" : ""}`} />
          </Button>
        </div>
      )}

      {testing && !connTest && (
        <div className="mb-4 rounded-lg bg-blue-50 border border-blue-200 p-4 flex items-center gap-3">
          <RefreshCw className="h-5 w-5 text-blue-600 animate-spin" />
          <p className="text-sm text-blue-700">Test de la connexion Cosium en cours...</p>
        </div>
      )}

      {/* Instructions + formulaire */}
      <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Key className="h-5 w-5" /> Renouveler le cookie Cosium
      </h3>

      <div className="space-y-3 mb-5">
        <div className="flex items-start gap-3">
          <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">1</span>
          <div>
            <p className="text-sm text-text-primary">
              Ouvrez Cosium dans votre navigateur et connectez-vous :
            </p>
            <a
              href="https://c1.cosium.biz/01CONE06488/classic/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline mt-1"
            >
              c1.cosium.biz <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">2</span>
          <div>
            <p className="text-sm text-text-primary">
              Appuyez sur <kbd className="bg-gray-100 px-1.5 py-0.5 rounded text-xs font-mono border">F12</kbd> → onglet
              {" "}<strong>Application</strong> → <strong>Cookies</strong> → <code className="bg-gray-100 px-1 rounded text-xs">c1.cosium.biz</code>
            </p>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">3</span>
          <div>
            <p className="text-sm text-text-primary">
              Copiez la valeur du cookie <code className="bg-gray-100 px-1 rounded text-xs font-mono">access_token</code> et collez-la ci-dessous :
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3 mb-4">
        <div>
          <label className="text-sm font-medium text-text-primary block mb-1">
            Cookie <code className="bg-gray-100 px-1 rounded text-xs">access_token</code> <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="Ex: GoRNM520XKaqk5NKGlI1s_XC_iY"
            value={cookieAccessToken}
            onChange={(e) => setCookieAccessToken(e.target.value)}
          />
        </div>
        <details className="group">
          <summary className="text-xs text-text-secondary cursor-pointer hover:text-text-primary">
            Avance : changer aussi le device-credential (rarement necessaire)
          </summary>
          <div className="mt-2">
            <label className="text-sm font-medium text-text-primary block mb-1">
              Cookie <code className="bg-gray-100 px-1 rounded text-xs">device-credential</code>
            </label>
            <input
              type="text"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Expire dans 1 an — changer uniquement si necessaire"
              value={cookieDeviceCredential}
              onChange={(e) => setCookieDeviceCredential(e.target.value)}
            />
          </div>
        </details>
      </div>

      {message && (
        <p className={`text-sm mb-3 ${message.type === "success" ? "text-emerald-600" : "text-red-600"}`}>
          {message.text}
        </p>
      )}

      <Button onClick={saveCookies} disabled={saving || !cookieAccessToken.trim()}>
        <Save className="h-4 w-4 mr-1.5" aria-hidden="true" />
        {saving ? "Enregistrement..." : "Enregistrer et tester"}
      </Button>
    </div>
  );
}
