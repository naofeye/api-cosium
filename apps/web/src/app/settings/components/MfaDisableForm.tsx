"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface MfaDisableFormProps {
  disablePassword: string;
  submitting: boolean;
  onPasswordChange: (password: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
}

export function MfaDisableForm({
  disablePassword,
  submitting,
  onPasswordChange,
  onSubmit,
  onCancel,
}: MfaDisableFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
      <p className="text-sm font-medium text-amber-900 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4" />
        Confirmez votre mot de passe pour desactiver MFA
      </p>
      <input
        type="password"
        placeholder="Mot de passe actuel"
        autoComplete="current-password"
        value={disablePassword}
        onChange={(e) => onPasswordChange(e.target.value)}
        className="w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-blue-100 bg-white"
      />
      <div className="flex gap-2">
        <Button type="submit" variant="danger" size="sm" loading={submitting} disabled={!disablePassword}>
          Desactiver MFA
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={onCancel}
          disabled={submitting}
        >
          Annuler
        </Button>
      </div>
    </form>
  );
}
