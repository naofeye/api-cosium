"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { CheckCircle, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ConnectCosiumResponse, CosiumFieldErrors } from "../helpers";
import { validateRequired } from "../helpers";

export function StepCosium({ onComplete, onSkip }: { onComplete: () => void; onSkip: () => void }) {
  const { toast } = useToast();
  const [form, setForm] = useState({ cosium_tenant: "", cosium_login: "", cosium_password: "" });
  const [errors, setErrors] = useState<CosiumFieldErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<"idle" | "success" | "error">("idle");
  const [apiError, setApiError] = useState("");

  const handleChange = (name: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [name]: value }));
    setConnectionStatus("idle");
    if (touched[name]) {
      setErrors((prev) => ({
        ...prev,
        [name]: validateRequired(
          value,
          name === "cosium_tenant" ? "Le code site" : name === "cosium_login" ? "L'identifiant" : "Le mot de passe",
        ),
      }));
    }
  };

  const handleBlur = (name: keyof typeof form) => {
    setTouched((prev) => ({ ...prev, [name]: true }));
    setErrors((prev) => ({
      ...prev,
      [name]: validateRequired(
        form[name],
        name === "cosium_tenant" ? "Le code site" : name === "cosium_login" ? "L'identifiant" : "Le mot de passe",
      ),
    }));
  };

  const isValid = form.cosium_tenant.trim() && form.cosium_login.trim() && form.cosium_password.trim();

  const handleTest = async () => {
    setApiError("");
    setLoading(true);
    setConnectionStatus("idle");
    try {
      await fetchJson<ConnectCosiumResponse>("/onboarding/connect-cosium", {
        method: "POST",
        body: JSON.stringify({
          cosium_tenant: form.cosium_tenant.trim(),
          cosium_login: form.cosium_login.trim(),
          cosium_password: form.cosium_password,
        }),
      });
      setConnectionStatus("success");
      toast("Connexion a Cosium reussie", "success");
    } catch (err) {
      setConnectionStatus("error");
      const msg = err instanceof Error ? err.message : "Impossible de se connecter a Cosium";
      setApiError(msg);
      toast(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const inputClass = (fieldName: keyof CosiumFieldErrors) =>
    cn(
      "w-full rounded-lg border bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-100",
      errors[fieldName] && touched[fieldName]
        ? "border-red-400 focus:border-red-500"
        : "border-gray-300 focus:border-blue-500",
    );

  return (
    <div className="space-y-5">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-gray-900">Connecter votre Cosium</h2>
        <p className="mt-1 text-sm text-gray-500">
          Reliez votre ERP Cosium pour synchroniser vos donnees automatiquement.
        </p>
      </div>
      <div>
        <label htmlFor="cosium_tenant" className="mb-1.5 block text-sm font-medium text-gray-700">
          Code site Cosium *
        </label>
        <input
          id="cosium_tenant"
          type="text"
          value={form.cosium_tenant}
          onChange={(e) => handleChange("cosium_tenant", e.target.value)}
          onBlur={() => handleBlur("cosium_tenant")}
          placeholder="mon-magasin"
          className={inputClass("cosium_tenant")}
        />
        {errors.cosium_tenant && touched.cosium_tenant && (
          <p className="mt-1 text-xs text-red-600">{errors.cosium_tenant}</p>
        )}
      </div>
      <div>
        <label htmlFor="cosium_login" className="mb-1.5 block text-sm font-medium text-gray-700">
          Identifiant Cosium *
        </label>
        <input
          id="cosium_login"
          type="text"
          value={form.cosium_login}
          onChange={(e) => handleChange("cosium_login", e.target.value)}
          onBlur={() => handleBlur("cosium_login")}
          placeholder="votre.identifiant"
          className={inputClass("cosium_login")}
        />
        {errors.cosium_login && touched.cosium_login && (
          <p className="mt-1 text-xs text-red-600">{errors.cosium_login}</p>
        )}
      </div>
      <div>
        <label htmlFor="cosium_password" className="mb-1.5 block text-sm font-medium text-gray-700">
          Mot de passe Cosium *
        </label>
        <input
          id="cosium_password"
          type="password"
          value={form.cosium_password}
          onChange={(e) => handleChange("cosium_password", e.target.value)}
          onBlur={() => handleBlur("cosium_password")}
          placeholder="Mot de passe Cosium"
          className={inputClass("cosium_password")}
          autoComplete="off"
        />
        {errors.cosium_password && touched.cosium_password && (
          <p className="mt-1 text-xs text-red-600">{errors.cosium_password}</p>
        )}
      </div>
      {connectionStatus === "success" && (
        <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          <CheckCircle className="h-5 w-5 shrink-0" />{" "}
          <span>Connexion reussie. Vos donnees Cosium sont accessibles.</span>
        </div>
      )}
      {connectionStatus === "error" && apiError && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <XCircle className="h-5 w-5 shrink-0" /> <span>{apiError}</span>
        </div>
      )}
      <div className="flex flex-col gap-3">
        <Button type="button" onClick={handleTest} disabled={!isValid} loading={loading} className="w-full">
          Tester la connexion
        </Button>
        {connectionStatus === "success" && (
          <Button type="button" onClick={onComplete} className="w-full">
            Continuer
          </Button>
        )}
        <Button type="button" variant="ghost" onClick={onSkip} className="w-full">
          Passer cette etape
        </Button>
      </div>
    </div>
  );
}
