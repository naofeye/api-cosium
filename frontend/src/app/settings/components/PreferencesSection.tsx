"use client";

import { Settings, Palette, List, Bell, Sun, Moon, Monitor } from "lucide-react";

type ThemeOption = "light" | "dark" | "auto";

interface Preferences {
  theme: ThemeOption;
  pageSize: number;
  emailNotifications: boolean;
}

interface PreferencesSectionProps {
  preferences: Preferences;
  prefsLoaded: boolean;
  onUpdatePreference: <K extends keyof Preferences>(key: K, value: Preferences[K]) => void;
}

const themeOptions: { value: ThemeOption; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Clair", icon: Sun },
  { value: "dark", label: "Sombre", icon: Moon },
  { value: "auto", label: "Auto", icon: Monitor },
];

const pageSizeOptions = [10, 25, 50, 100];

export function PreferencesSection({
  preferences,
  prefsLoaded,
  onUpdatePreference,
}: PreferencesSectionProps) {
  return (
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
                    onClick={() => onUpdatePreference("theme", opt.value)}
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
                    onClick={() => onUpdatePreference("pageSize", size)}
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
              onClick={() => onUpdatePreference("emailNotifications", !preferences.emailNotifications)}
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
  );
}
