"use client";

import { useCallback, useEffect, useState } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Shield, Check, Copy, AlertTriangle, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

type EnrollmentStep = "idle" | "enrolling" | "verifying" | "confirming-disable";

interface MfaSetupResponse {
  secret: string;
  otpauth_uri: string;
  issuer: string;
}

interface MfaStatusResponse {
  enabled: boolean;
}

interface MfaBackupCodesResponse {
  codes: string[];
  remaining: number;
}

interface MfaBackupCodesCountResponse {
  remaining: number;
}

export function MfaSection() {
  const { toast } = useToast();
  const [enabled, setEnabled] = useState<boolean | null>(null);
  const [backupRemaining, setBackupRemaining] = useState<number | null>(null);
  const [step, setStep] = useState<EnrollmentStep>("idle");
  const [enrollment, setEnrollment] = useState<MfaSetupResponse | null>(null);
  const [verifyCode, setVerifyCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [newBackupCodes, setNewBackupCodes] = useState<string[] | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const refreshStatus = useCallback(async () => {
    try {
      const status = await fetchJson<MfaStatusResponse>("/auth/mfa/status");
      setEnabled(status.enabled);
      if (status.enabled) {
        const count = await fetchJson<MfaBackupCodesCountResponse>(
          "/auth/mfa/backup-codes/count",
        );
        setBackupRemaining(count.remaining);
      } else {
        setBackupRemaining(null);
      }
    } catch {
      setEnabled(false);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const startEnrollment = async () => {
    setSubmitting(true);
    try {
      const resp = await fetchJson<MfaSetupResponse>("/auth/mfa/setup", { method: "POST" });
      setEnrollment(resp);
      setStep("enrolling");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Impossible de demarrer l'enrolement MFA", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const confirmEnrollment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^\d{6}$/.test(verifyCode)) {
      toast("Le code doit etre 6 chiffres", "error");
      return;
    }
    setSubmitting(true);
    try {
      await fetchJson("/auth/mfa/enable", {
        method: "POST",
        body: JSON.stringify({ code: verifyCode }),
      });
      const generated = await fetchJson<MfaBackupCodesResponse>(
        "/auth/mfa/backup-codes/generate",
        { method: "POST" },
      );
      setNewBackupCodes(generated.codes);
      setEnabled(true);
      setBackupRemaining(generated.remaining);
      setEnrollment(null);
      setVerifyCode("");
      setStep("idle");
      toast("Authentification a deux facteurs activee", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Code invalide", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const cancelEnrollment = () => {
    setEnrollment(null);
    setVerifyCode("");
    setStep("idle");
  };

  const regenerateBackupCodes = async () => {
    if (!window.confirm("Generer de nouveaux codes de secours ? Les anciens seront invalides.")) return;
    setSubmitting(true);
    try {
      const resp = await fetchJson<MfaBackupCodesResponse>(
        "/auth/mfa/backup-codes/generate",
        { method: "POST" },
      );
      setNewBackupCodes(resp.codes);
      setBackupRemaining(resp.remaining);
      toast("Nouveaux codes generes", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur generation", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const confirmDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await fetchJson("/auth/mfa/disable", {
        method: "POST",
        body: JSON.stringify({ password: disablePassword }),
      });
      setEnabled(false);
      setBackupRemaining(null);
      setDisablePassword("");
      setStep("idle");
      toast("Authentification a deux facteurs desactivee", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Mot de passe incorrect", "error");
    } finally {
      setSubmitting(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(
      () => toast("Copie", "success"),
      () => toast("Echec de la copie", "error"),
    );
  };

  const copyAllCodes = () => {
    if (newBackupCodes) copyToClipboard(newBackupCodes.join("\n"));
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <div className="flex items-center gap-4 mb-6">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-50 dark:bg-indigo-900/20">
          <Shield className="h-6 w-6 text-indigo-600" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-text-primary">Authentification a deux facteurs</h2>
          <p className="text-sm text-text-secondary">
            Renforce la securite de votre compte avec un code TOTP a usage unique.
          </p>
        </div>
      </div>

      {/* Etat inconnu (loading) */}
      {enabled === null && (
        <div className="text-sm text-text-secondary">Chargement...</div>
      )}

      {/* Etat : active */}
      {enabled === true && step === "idle" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-emerald-700">
            <Check className="h-4 w-4" />
            <span className="font-medium">MFA active sur votre compte</span>
          </div>
          {backupRemaining !== null && (
            <div className="rounded-lg border border-border bg-gray-50 p-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">Codes de secours restants</span>
                <span className="font-semibold text-text-primary tabular-nums">
                  {backupRemaining} / 10
                </span>
              </div>
              {backupRemaining <= 2 && (
                <p className="mt-2 text-xs text-amber-700 flex items-center gap-1">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Il vous reste peu de codes. Generez-en de nouveaux.
                </p>
              )}
            </div>
          )}
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={regenerateBackupCodes} disabled={submitting}>
              <KeyRound className="h-4 w-4 mr-1" />
              Generer nouveaux codes
            </Button>
            <Button variant="danger" size="sm" onClick={() => setStep("confirming-disable")} disabled={submitting}>
              Desactiver MFA
            </Button>
          </div>
        </div>
      )}

      {/* Etat : desactive */}
      {enabled === false && step === "idle" && (
        <div className="rounded-lg border border-dashed border-border p-4">
          <p className="text-sm text-text-secondary mb-3">
            MFA n&apos;est pas active sur votre compte. Nous recommandons vivement de l&apos;activer.
          </p>
          <Button size="sm" onClick={startEnrollment} loading={submitting}>
            Activer MFA
          </Button>
        </div>
      )}

      {/* Etape enrolling : QR + verif */}
      {step === "enrolling" && enrollment && (
        <form onSubmit={confirmEnrollment} className="space-y-4">
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
                    onClick={() => copyToClipboard(enrollment.secret)}
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
              onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, ""))}
              className="w-40 rounded-lg border border-border px-4 py-2.5 text-center text-lg font-mono tracking-widest outline-none focus:border-primary focus:ring-2 focus:ring-blue-100"
            />
          </div>

          <div className="flex gap-2">
            <Button type="submit" loading={submitting} disabled={verifyCode.length !== 6}>
              Valider et activer
            </Button>
            <Button type="button" variant="outline" onClick={cancelEnrollment} disabled={submitting}>
              Annuler
            </Button>
          </div>
        </form>
      )}

      {/* Etape confirming-disable */}
      {step === "confirming-disable" && (
        <form onSubmit={confirmDisable} className="space-y-3 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="text-sm font-medium text-amber-900 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            Confirmez votre mot de passe pour desactiver MFA
          </p>
          <input
            type="password"
            placeholder="Mot de passe actuel"
            autoComplete="current-password"
            value={disablePassword}
            onChange={(e) => setDisablePassword(e.target.value)}
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
              onClick={() => {
                setStep("idle");
                setDisablePassword("");
              }}
              disabled={submitting}
            >
              Annuler
            </Button>
          </div>
        </form>
      )}

      {/* Modal codes de secours affiches une seule fois */}
      {newBackupCodes && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
                <KeyRound className="h-5 w-5 text-amber-700" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-gray-900">Codes de secours</h3>
                <p className="text-xs text-gray-500">Affiches une seule fois. Conservez-les en lieu sur.</p>
              </div>
            </div>
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 mb-4">
              <p className="text-xs text-amber-800 mb-3">
                Chaque code est utilisable une seule fois si vous perdez votre telephone.
                Stockez-les dans un gestionnaire de mots de passe ou imprimez-les.
              </p>
              <div className="grid grid-cols-2 gap-2 font-mono text-sm">
                {newBackupCodes.map((code) => (
                  <code key={code} className="rounded bg-white border border-amber-200 px-2 py-1 text-center">
                    {code}
                  </code>
                ))}
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <Button variant="outline" size="sm" onClick={copyAllCodes}>
                <Copy className="h-4 w-4 mr-1" />
                Copier tout
              </Button>
              <Button size="sm" onClick={() => setNewBackupCodes(null)}>
                J&apos;ai note mes codes
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
