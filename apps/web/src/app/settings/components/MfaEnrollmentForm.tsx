"use client";

import { QRCodeSVG } from "qrcode.react";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/Button";
import type { MfaSetupResponse } from "./MfaTypes";

interface MfaEnrollmentFormProps {
  enrollment: MfaSetupResponse;
  verifyCode: string;
  submitting: boolean;
  onVerifyCodeChange: (code: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  onCopySecret: (secret: string) => void;
}

export function MfaEnrollmentForm({
  enrollment,
  verifyCode,
  submitting,
  onVerifyCodeChange,
  onSubmit,
  onCancel,
  onCopySecret,
}: MfaEnrollmentFormProps) {
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="rounded-lg border border-border bg-gray-50 p-4">
        <p className="text-sm font-medium text-text-primary mb-3">
          1. Scannez ce QR code dans votre application (Google Authenticator, 1Password, Authy...)
        </p>
        <div className="flex items-start gap-4">
          <div className="rounded-lg bg-white p-3 border border-border">
            <QRCodeSVG value={enrollment.otpauth_uri} size={160} level="M" />
          </div>
          <div className="flex-1 text-xs space-y-2">
            <p className="text-text-secondary">Ou saisissez le secret manuellement :</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-white border border-border px-2 py-1.5 font-mono text-xs break-all">
                {enrollment.secret}
              </code>
              <button
                type="button"
                onClick={() => onCopySecret(enrollment.secret)}
                className="rounded p-1.5 text-text-secondary hover:bg-gray-200"
                aria-label="Copier le secret"
                title="Copier"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div>
        <label htmlFor="mfa-verify-code" className="block text-sm font-medium text-text-secondary mb-1">
          2. Saisissez le code a 6 chiffres affiche par votre application
        </label>
        <input
          id="mfa-verify-code"
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          pattern="[0-9]{6}"
          placeholder="123456"
          value={verifyCode}
          onChange={(e) => onVerifyCodeChange(e.target.value.replace(/\D/g, ""))}
          className="w-40 rounded-lg border border-border px-4 py-2.5 text-center text-lg font-mono tracking-widest outline-none focus:border-primary focus:ring-2 focus:ring-blue-100"
        />
      </div>

      <div className="flex gap-2">
        <Button type="submit" loading={submitting} disabled={verifyCode.length !== 6}>
          Valider et activer
        </Button>
        <Button type="button" variant="outline" onClick={onCancel} disabled={submitting}>
          Annuler
        </Button>
      </div>
    </form>
  );
}
