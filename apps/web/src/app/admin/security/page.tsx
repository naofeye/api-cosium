"use client";

import { useCallback, useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/LoadingState";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { Shield, AlertTriangle, Info } from "lucide-react";

interface TenantSecurity {
  require_admin_mfa: boolean;
}

export default function AdminSecurityPage() {
  const { toast } = useToast();
  const [data, setData] = useState<TenantSecurity | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const resp = await fetchJson<TenantSecurity>("/admin/tenant/security");
      setData(resp);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Erreur chargement");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggleRequireAdminMfa = async (nextValue: boolean) => {
    if (nextValue) {
      const ok = window.confirm(
        "Activer l'exigence MFA pour les admins ?\n\n" +
          "Tous les administrateurs de ce magasin qui n'ont pas encore configure MFA " +
          "seront refuses au prochain login avec un message leur demandant de configurer MFA.\n\n" +
          "Confirmez-vous ?",
      );
      if (!ok) return;
    }
    setSaving(true);
    try {
      const resp = await fetchJson<TenantSecurity>("/admin/tenant/security", {
        method: "PATCH",
        body: JSON.stringify({ require_admin_mfa: nextValue }),
      });
      setData(resp);
      toast(
        nextValue ? "MFA exigee pour les admins" : "MFA non exigee",
        "success",
      );
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur mise a jour", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageLayout
      title="Securite du magasin"
      description="Politique d'authentification pour ce magasin (tenant)"
      breadcrumb={[{ label: "Administration", href: "/admin/users" }, { label: "Securite" }]}
    >
      {loading && <LoadingState text="Chargement de la politique..." />}
      {errorMsg && !loading && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {errorMsg}
        </div>
      )}

      {!loading && data && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <div className="flex items-center gap-4 mb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50">
              <Shield className="h-6 w-6 text-indigo-600" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Authentification a deux facteurs</h2>
              <p className="text-sm text-text-secondary">
                Forcer tous les administrateurs de ce magasin a activer MFA/TOTP.
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-gray-50 p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <p className="text-sm font-medium text-text-primary">
                  Exiger MFA pour les administrateurs
                </p>
                <p className="mt-1 text-xs text-text-secondary">
                  Si active, un administrateur sans MFA configure sera bloque au login
                  avec le message &quot;MFA_SETUP_REQUIRED&quot; et devra activer MFA avant
                  de pouvoir acceder au magasin.
                </p>
              </div>
              <Button
                size="sm"
                variant={data.require_admin_mfa ? "danger" : "primary"}
                onClick={() => toggleRequireAdminMfa(!data.require_admin_mfa)}
                loading={saving}
              >
                {data.require_admin_mfa ? "Desactiver" : "Activer"}
              </Button>
            </div>
            <div className="mt-3 flex items-center gap-2 text-xs">
              <span className="text-text-secondary">Etat :</span>
              {data.require_admin_mfa ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 border border-emerald-200 px-2 py-0.5 text-emerald-700 font-medium">
                  Activee
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 border border-gray-200 px-2 py-0.5 text-gray-600 font-medium">
                  Desactivee
                </span>
              )}
            </div>
          </div>

          {data.require_admin_mfa && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
              <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
              <p>
                Les admins sans MFA seront refuses. Assurez-vous qu&apos;au moins un admin
                a deja MFA configure pour eviter un lockout.
              </p>
            </div>
          )}

          <div className="mt-6 flex items-start gap-2 rounded-lg border border-blue-100 bg-blue-50 p-3 text-xs text-blue-900">
            <Info className="h-4 w-4 mt-0.5 shrink-0" />
            <p>
              Chaque utilisateur peut activer MFA depuis sa page{" "}
              <strong>Parametres &rarr; Authentification a deux facteurs</strong>.
              Les changements de politique sont audites.
            </p>
          </div>
        </div>
      )}
    </PageLayout>
  );
}
