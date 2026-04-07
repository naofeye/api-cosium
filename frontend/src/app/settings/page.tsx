"use client";

import { useEffect, useState, useCallback } from "react";
import { PageLayout } from "@/components/layout/PageLayout";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { ProfileSection } from "./components/ProfileSection";
import { SecuritySection } from "./components/SecuritySection";
import { PreferencesSection } from "./components/PreferencesSection";
import { SettingsLinks } from "./components/SettingsLinks";
import { AboutSection } from "./components/AboutSection";

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

  const inputClasses =
    "w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 bg-white dark:bg-gray-800 dark:text-white";

  return (
    <PageLayout title="Parametres" breadcrumb={[{ label: "Parametres" }]}>
      <ProfileSection
        profile={profile}
        editName={editName}
        editEmail={editEmail}
        onNameChange={setEditName}
        onEmailChange={setEditEmail}
        inputClasses={inputClasses}
      />
      <SecuritySection
        oldPassword={oldPassword}
        newPassword={newPassword}
        changing={changing}
        onOldPasswordChange={setOldPassword}
        onNewPasswordChange={setNewPassword}
        onSubmit={handleChangePassword}
        inputClasses={inputClasses}
      />
      <PreferencesSection
        preferences={preferences}
        prefsLoaded={prefsLoaded}
        onUpdatePreference={updatePreference}
      />
      <SettingsLinks />
      <AboutSection />
    </PageLayout>
  );
}
