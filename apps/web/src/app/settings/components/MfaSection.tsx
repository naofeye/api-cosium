"use client";

import { useCallback, useEffect, useState } from "react";
import { Shield, Check, AlertTriangle, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { MfaEnrollmentForm } from "./MfaEnrollmentForm";
import { MfaDisableForm } from "./MfaDisableForm";
import { MfaBackupCodesModal } from "./MfaBackupCodesModal";
import type {
  EnrollmentStep,
  MfaSetupResponse,
  MfaStatusResponse,
  MfaBackupCodesResponse,
  MfaBackupCodesCountResponse,
} from "./MfaTypes";

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
        <MfaEnrollmentForm
          enrollment={enrollment}
          verifyCode={verifyCode}
          submitting={submitting}
          onVerifyCodeChange={setVerifyCode}
          onSubmit={confirmEnrollment}
          onCancel={cancelEnrollment}
          onCopySecret={copyToClipboard}
        />
      )}

      {/* Etape confirming-disable */}
      {step === "confirming-disable" && (
        <MfaDisableForm
          disablePassword={disablePassword}
          submitting={submitting}
          onPasswordChange={setDisablePassword}
          onSubmit={confirmDisable}
          onCancel={() => {
            setStep("idle");
            setDisablePassword("");
          }}
        />
      )}

      {/* Modal codes de secours affiches une seule fois */}
      {newBackupCodes && (
        <MfaBackupCodesModal
          codes={newBackupCodes}
          onCopyAll={copyAllCodes}
          onDismiss={() => setNewBackupCodes(null)}
        />
      )}
    </div>
  );
}
