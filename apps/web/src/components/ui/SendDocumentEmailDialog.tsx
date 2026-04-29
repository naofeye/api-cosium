"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Loader2, Send, X } from "lucide-react";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";

export interface SendDocumentEmailDialogProps {
  open: boolean;
  onClose: () => void;
  /** Endpoint relatif a /api/v1, ex: "/devis/42/send-email". */
  endpoint: string;
  /** Numero du document affiche dans le header et l'objet par defaut. */
  documentNumero: string;
  /** Type de document en francais (singulier minuscule), ex: "devis", "facture". */
  documentLabel: string;
  /** Email du client si connu. */
  defaultRecipient?: string | null;
  /** Sujet par defaut. Si absent, "Votre {documentLabel} {documentNumero}". */
  defaultSubject?: string;
  /** Message par defaut. Si absent, un message generique est utilise. */
  defaultMessage?: string;
  onSent?: (response: { to: string }) => void;
}

interface SendEmailResponse {
  sent: boolean;
  to: string;
}

function buildDefaultMessage(label: string): string {
  return `Bonjour,\n\nVeuillez trouver ci-joint votre ${label}. Nous restons a votre disposition pour toute question.\n\nCordialement,\nL'equipe OptiFlow`;
}

export function SendDocumentEmailDialog({
  open,
  onClose,
  endpoint,
  documentNumero,
  documentLabel,
  defaultRecipient,
  defaultSubject,
  defaultMessage,
  onSent,
}: SendDocumentEmailDialogProps) {
  const { toast } = useToast();
  const initialSubject = defaultSubject ?? `Votre ${documentLabel} ${documentNumero}`;
  const initialMessage = defaultMessage ?? buildDefaultMessage(documentLabel);

  const [to, setTo] = useState(defaultRecipient ?? "");
  const [subject, setSubject] = useState(initialSubject);
  const [message, setMessage] = useState(initialMessage);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) {
      setTo(defaultRecipient ?? "");
      setSubject(initialSubject);
      setMessage(initialMessage);
    }
  }, [open, defaultRecipient, documentNumero, documentLabel, initialSubject, initialMessage]);

  if (!open) return null;

  const isValid = to.trim().length > 0 && /\S+@\S+\.\S+/.test(to);
  const headerLabel = documentLabel.charAt(0).toUpperCase() + documentLabel.slice(1);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!isValid || sending) return;
    setSending(true);
    try {
      const result = await fetchJson<SendEmailResponse>(endpoint, {
        method: "POST",
        body: JSON.stringify({
          to: to.trim(),
          subject: subject.trim() || undefined,
          message: message.trim() || undefined,
        }),
      });
      toast(`${headerLabel} envoye a ${result.to}`, "success");
      onSent?.(result);
      onClose();
    } catch {
      // fetchJson dispatches a global api-error event handled by the toast layer
    } finally {
      setSending(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-label={`Envoyer ${documentLabel} par email`}
    >
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl mx-4"
      >
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Envoyer {documentLabel === "facture" ? "la" : "le"} {documentLabel} {documentNumero}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-text-secondary hover:bg-gray-100 transition-colors"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          <p className="text-xs text-text-secondary">
            Le PDF {documentLabel === "facture" ? "de la" : "du"} {documentLabel} sera attache automatiquement.
          </p>

          <div>
            <label
              htmlFor="senddoc-email-to"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Destinataire *
            </label>
            <input
              id="senddoc-email-to"
              type="email"
              required
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="client@example.com"
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
            {!defaultRecipient && (
              <p className="mt-1 text-xs text-text-secondary">
                Le client n&apos;a pas d&apos;email enregistre. Saisissez un destinataire.
              </p>
            )}
          </div>

          <div>
            <label
              htmlFor="senddoc-email-subject"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Objet
            </label>
            <input
              id="senddoc-email-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              maxLength={200}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label
              htmlFor="senddoc-email-message"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Message personnalise
            </label>
            <textarea
              id="senddoc-email-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={6}
              maxLength={2000}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-y"
            />
            <p className="mt-1 text-xs text-text-secondary">
              {message.length}/2000 caracteres
            </p>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-gray-50 transition-colors"
            disabled={sending}
          >
            Annuler
          </button>
          <button
            type="submit"
            disabled={!isValid || sending}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
            {sending ? "Envoi en cours..." : "Envoyer"}
          </button>
        </div>
      </form>
    </div>
  );
}
