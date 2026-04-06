"use client";

import { useEffect, useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import {
  User,
  CreditCard,
  Brain,
  Database,
  HelpCircle,
  Lock,
  Shield,
  Palette,
  Settings,
  Info,
  Sun,
  Moon,
  Monitor,
  List,
  Bell,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";

interface UserProfile {
  id: number;
  email: string;
  full_name?: string;
  role: string;
}

type ThemeOption = "light" | "dark" | "auto";

interface Preferences {
  theme: ThemeOption;
  pageSize: number;
  emailNotifications: boolean;
}

const DEFAULT_PREFERENCES: Preferences = {
  theme: "light",
  pageSize: 25,
  emailNotifications: true,
};

function loadPreferences(): Preferences {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES;
  try {
    const raw = localStorage.getItem("optiflow_preferences");
    if (raw) return { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) };
  } catch {
    // ignore
  }
  return DEFAULT_PREFERENCES;
}

function savePreferences(prefs: Preferences): void {
  localStorage.setItem("optiflow_preferences", JSON.stringify(prefs));
}

function applyTheme(theme: ThemeOption): void {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
    localStorage.setItem("theme", "dark");
  } else if (theme === "light") {
    root.classList.remove("dark");
    localStorage.setItem("theme", "light");
  } else {
    // auto: follow system preference
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    if (prefersDark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("theme", "auto");
  }
}

export default function SettingsPage() {
  const { toast } = useToast();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [editName, setEditName] = useState("");
  const [editEmail, setEditEmail] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changing, setChanging] = useState(false);
  const [preferences, setPreferences] = useState<Preferences>(DEFAULT_PREFERENCES);
  const [prefsLoaded, setPrefsLoaded] = useState(false);

  useEffect(() => {
    fetchJson<UserProfile>("/auth/me")
      .then((p) => {
        setProfile(p);
        setEditName(p.full_name || "");
        setEditEmail(p.email);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const prefs = loadPreferences();
    setPreferences(prefs);
    setPrefsLoaded(true);
    applyTheme(prefs.theme);
  }, []);

  const updatePreference = useCallback(
    <K extends keyof Preferences>(key: K, value: Preferences[K]) => {
      setPreferences((prev) => {
        const next = { ...prev, [key]: value };
        savePreferences(next);
        if (key === "theme") applyTheme(value as ThemeOption);
        return next;
      });
      toast("Preference enregistree", "success");
    },
    [toast],
  );

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

  const themeOptions: { value: ThemeOption; label: string; icon: typeof Sun }[] = [
    { value: "light", label: "Clair", icon: Sun },
    { value: "dark", label: "Sombre", icon: Moon },
    { value: "auto", label: "Auto", icon: Monitor },
  ];

  const pageSizeOptions = [10, 25, 50, 100];

  const inputClasses =
    "w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 bg-white dark:bg-gray-800 dark:text-white";

  return (
    <PageLayout title="Parametres" breadcrumb={[{ label: "Parametres" }]}>
      {/* ── Section 1: Profil utilisateur ── */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-white">
            <User className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Profil utilisateur</h2>
            <p className="text-sm text-text-secondary">
              Gerez vos informations personnelles
            </p>
          </div>
        </div>

        <div className="max-w-md space-y-4">
          <div>
            <label htmlFor="profile-name" className="block text-sm font-medium text-text-secondary mb-1">
              Nom complet
            </label>
            <input
              id="profile-name"
              type="text"
              placeholder="Votre nom"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className={inputClasses}
            />
          </div>
          <div>
            <label htmlFor="profile-email" className="block text-sm font-medium text-text-secondary mb-1">
              Adresse email
            </label>
            <input
              id="profile-email"
              type="email"
              placeholder="votre@email.com"
              value={editEmail}
              onChange={(e) => setEditEmail(e.target.value)}
              className={inputClasses}
            />
          </div>
          {profile && (
            <p className="text-xs text-text-secondary">
              Role : <span className="font-medium capitalize">{profile.role}</span>
            </p>
          )}
        </div>
      </div>

      {/* ── Section 2: Securite ── */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/20">
            <Shield className="h-6 w-6 text-danger" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Securite</h2>
            <p className="text-sm text-text-secondary">Mot de passe et authentification</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Change password */}
          <form onSubmit={handleChangePassword}>
            <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <Lock className="h-4 w-4" />
              Changer le mot de passe
            </h3>
            <div className="space-y-3">
              <div>
                <label htmlFor="old-password" className="block text-sm font-medium text-text-secondary mb-1">
                  Mot de passe actuel
                </label>
                <input
                  id="old-password"
                  type="password"
                  placeholder="Mot de passe actuel"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  autoComplete="current-password"
                  className={inputClasses}
                />
              </div>
              <div>
                <label htmlFor="new-password" className="block text-sm font-medium text-text-secondary mb-1">
                  Nouveau mot de passe
                </label>
                <input
                  id="new-password"
                  type="password"
                  placeholder="8 caracteres minimum"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  autoComplete="new-password"
                  className={inputClasses}
                />
              </div>
              <Button type="submit" size="sm" disabled={!oldPassword || !newPassword} loading={changing}>
                Modifier le mot de passe
              </Button>
            </div>
          </form>

          {/* 2FA placeholder */}
          <div>
            <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
              <Shield className="h-4 w-4" />
              Authentification a deux facteurs (2FA)
            </h3>
            <div className="rounded-lg border border-dashed border-border p-4 text-center">
              <p className="text-sm text-text-secondary mb-3">
                Renforcez la securite de votre compte avec la double authentification.
              </p>
              <Button variant="outline" size="sm" disabled>
                Bientot disponible
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Section 3: Preferences ── */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-amber-50 dark:bg-amber-900/20">
            <Settings className="h-6 w-6 text-amber-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">Preferences</h2>
            <p className="text-sm text-text-secondary">Personnalisez votre experience</p>
          </div>
        </div>

        {prefsLoaded && (
          <div className="space-y-6 max-w-lg">
            {/* Theme */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
                <Palette className="h-4 w-4" />
                Theme
              </label>
              <div className="flex gap-2">
                {themeOptions.map((opt) => {
                  const Icon = opt.icon;
                  const active = preferences.theme === opt.value;
                  return (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => updatePreference("theme", opt.value)}
                      className={`flex items-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                        active
                          ? "border-primary bg-blue-50 text-primary dark:bg-blue-900/30"
                          : "border-border text-text-secondary hover:border-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                      {opt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Page size */}
            <div>
              <label className="flex items-center gap-2 text-sm font-medium text-text-primary mb-2">
                <List className="h-4 w-4" />
                Elements par page
              </label>
              <div className="flex gap-2">
                {pageSizeOptions.map((size) => {
                  const active = preferences.pageSize === size;
                  return (
                    <button
                      key={size}
                      type="button"
                      onClick={() => updatePreference("pageSize", size)}
                      className={`rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                        active
                          ? "border-primary bg-blue-50 text-primary dark:bg-blue-900/30"
                          : "border-border text-text-secondary hover:border-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
                      }`}
                    >
                      {size}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Email notifications */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm font-medium text-text-primary">
                <Bell className="h-4 w-4" />
                Notifications par email
              </label>
              <button
                type="button"
                onClick={() => updatePreference("emailNotifications", !preferences.emailNotifications)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  preferences.emailNotifications ? "bg-primary" : "bg-gray-300 dark:bg-gray-600"
                }`}
                role="switch"
                aria-checked={preferences.emailNotifications}
                aria-label="Activer les notifications par email"
              >
                <span
                  className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                    preferences.emailNotifications ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Liens vers les sous-pages ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {settingsLinks.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-start gap-4 rounded-xl border border-border bg-bg-card p-5 shadow-sm hover:border-primary hover:shadow-md transition-all"
          >
            <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-2.5">
              <link.icon className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary">{link.label}</h3>
              <p className="text-xs text-text-secondary mt-0.5">{link.description}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* ── Section 4: A propos ── */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gray-100 dark:bg-gray-800">
            <Info className="h-6 w-6 text-text-secondary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-text-primary">A propos</h2>
            <p className="text-sm text-text-secondary">Informations sur OptiFlow AI</p>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          <div className="space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Version</span>
              <span className="font-medium text-text-primary">0.1.0 (MVP)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Backend</span>
              <span className="font-medium text-text-primary">Python 3.12 + FastAPI</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Frontend</span>
              <span className="font-medium text-text-primary">Next.js 15 + React 19</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Base de donnees</span>
              <span className="font-medium text-text-primary">PostgreSQL 16</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Cache</span>
              <span className="font-medium text-text-primary">Redis 7</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border">
              <span className="text-text-secondary">Stockage</span>
              <span className="font-medium text-text-primary">MinIO (S3)</span>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-primary hover:underline"
            aria-label="Voir le depot GitHub"
          >
            <ExternalLink className="h-4 w-4" />
            Voir sur GitHub
          </a>
        </div>
      </div>

      {/* ── Aide ── */}
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
