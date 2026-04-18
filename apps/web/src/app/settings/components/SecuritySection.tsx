"use client";

import { Lock, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface SecuritySectionProps {
  oldPassword: string;
  newPassword: string;
  changing: boolean;
  onOldPasswordChange: (value: string) => void;
  onNewPasswordChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  inputClasses: string;
}

export function SecuritySection({
  oldPassword,
  newPassword,
  changing,
  onOldPasswordChange,
  onNewPasswordChange,
  onSubmit,
  inputClasses,
}: SecuritySectionProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <div className="flex items-center gap-4 mb-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-50 dark:bg-red-900/20">
          <ShieldCheck className="h-6 w-6 text-danger" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Securite</h2>
          <p className="text-sm text-text-secondary">Changer votre mot de passe</p>
        </div>
      </div>

      {/* Change password */}
      <form onSubmit={onSubmit}>
        <h3 className="text-sm font-semibold text-text-primary mb-3 flex items-center gap-2">
          <Lock className="h-4 w-4" />
          Changer le mot de passe
        </h3>
        <div className="space-y-3 max-w-md">
          <div>
            <label htmlFor="old-password" className="block text-sm font-medium text-text-secondary mb-1">
              Mot de passe actuel
            </label>
            <input
              id="old-password"
              type="password"
              placeholder="Mot de passe actuel"
              value={oldPassword}
              onChange={(e) => onOldPasswordChange(e.target.value)}
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
              onChange={(e) => onNewPasswordChange(e.target.value)}
              autoComplete="new-password"
              className={inputClasses}
            />
          </div>
          <Button type="submit" size="sm" disabled={!oldPassword || !newPassword} loading={changing}>
            Modifier le mot de passe
          </Button>
        </div>
      </form>
    </div>
  );
}
