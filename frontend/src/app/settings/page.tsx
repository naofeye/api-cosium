"use client";

import { useEffect, useState } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { User, CreditCard, Brain, Database, HelpCircle, Lock } from "lucide-react";
import Link from "next/link";

interface UserProfile {
  id: number;
  email: string;
  role: string;
}

export default function SettingsPage() {
  const { toast } = useToast();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    fetchJson<UserProfile>("/auth/me")
      .then(setProfile)
      .catch(() => {});
  }, []);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword.length < 8) {
      toast("Le mot de passe doit contenir au moins 8 caracteres", "error");
      return;
    }
    setChanging(true);
    try {
      await fetchJson("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
      });
      toast("Mot de passe modifie avec succes", "success");
      setOldPassword("");
      setNewPassword("");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors du changement", "error");
    } finally {
      setChanging(false);
    }
  };

  const settingsLinks = [
    {
      href: "/settings/billing",
      label: "Facturation et abonnement",
      description: "Plan actuel, historique des factures",
      icon: CreditCard,
    },
    {
      href: "/settings/ai-usage",
      label: "Consommation IA",
      description: "Usage du copilote, quotas, historique",
      icon: Brain,
    },
    {
      href: "/settings/erp",
      label: "Connexion ERP",
      description: "Statut Cosium, synchronisation, configuration",
      icon: Database,
    },
  ];

  return (
    <PageLayout title="Parametres" breadcrumb={[{ label: "Parametres" }]}>
      {/* Profil */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white">
            <User className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Profil</h2>
            {profile && (
              <p className="text-sm text-text-secondary">
                {profile.email} — {profile.role}
              </p>
            )}
          </div>
        </div>

        <form onSubmit={handleChangePassword} className="max-w-md">
          <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Lock className="h-4 w-4" />
            Changer le mot de passe
          </h3>
          <div className="space-y-3">
            <input
              type="password"
              placeholder="Mot de passe actuel"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              className="w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100"
            />
            <input
              type="password"
              placeholder="Nouveau mot de passe (8 caracteres min.)"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100"
            />
            <Button type="submit" size="sm" disabled={!oldPassword || !newPassword} loading={changing}>
              Modifier le mot de passe
            </Button>
          </div>
        </form>
      </div>

      {/* Liens vers les sous-pages */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {settingsLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-start gap-4 rounded-xl border border-border bg-bg-card p-5 shadow-sm hover:border-primary hover:shadow-md transition-all"
          >
            <div className="rounded-lg bg-blue-50 p-2.5">
              <link.icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">{link.label}</h3>
              <p className="text-xs text-text-secondary mt-0.5">{link.description}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* Aide */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <HelpCircle className="h-5 w-5 text-text-secondary" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Besoin d&apos;aide ?</h3>
            <p className="text-xs text-text-secondary mt-0.5">
              Contactez le support a support@optiflow.ai ou consultez la documentation.
            </p>
          </div>
        </div>
      </div>
    </PageLayout>
  );
}
