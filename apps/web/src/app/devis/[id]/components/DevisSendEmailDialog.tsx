"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Loader2, Send, X } from "lucide-react";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";

interface DevisSendEmailDialogProps {
  open: boolean;
  onClose: () => void;
  devisId: number;
  devisNumero: string;
  defaultRecipient?: string | null;
  onSent?: () => void;
}

interface SendEmailResponse {
  sent: boolean;
  to: string;
  devis_id: number;
}

const DEFAULT_MESSAGE =
  "Bonjour,\n\nVeuillez trouver ci-joint votre devis. Nous restons a votre disposition pour toute question.\n\nCordialement,\nL'equipe OptiFlow";

export function DevisSendEmailDialog({
  open,
  onClose,
  devisId,
  devisNumero,
  defaultRecipient,
  onSent,
}: DevisSendEmailDialogProps) {
  const { toast } = useToast();
  const [to, setTo] = useState(defaultRecipient ?? "");
  const [subject, setSubject] = useState(`Votre devis ${devisNumero}`);
  const [message, setMessage] = useState(DEFAULT_MESSAGE);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (open) {
      setTo(defaultRecipient ?? "");
      setSubject(`Votre devis ${devisNumero}`);
      setMessage(DEFAULT_MESSAGE);
    }
  }, [open, defaultRecipient, devisNumero]);

  if (!open) return null;

  const isValid = to.trim().length > 0 && /\S+@\S+\.\S+/.test(to);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!isValid || sending) return;
    setSending(true);
    try {
      const result = await fetchJson<SendEmailResponse>(
        `/devis/${devisId}/send-email`,
        {
          method: "POST",
          body: JSON.stringify({
            to: to.trim(),
            subject: subject.trim() || undefined,
            message: message.trim() || undefined,
          }),
        },
      );
      toast(`Devis envoye a ${result.to}`, "success");
      onSent?.();
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
      aria-label="Envoyer le devis par email"
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
            Envoyer le devis {devisNumero}
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
            Le PDF du devis sera attache automatiquement.
          </p>

          <div>
            <label
              htmlFor="devis-email-to"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Destinataire *
            </label>
            <input
              id="devis-email-to"
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
              htmlFor="devis-email-subject"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Objet
            </label>
            <input
              id="devis-email-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              maxLength={200}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label
              htmlFor="devis-email-message"
              className="block text-sm font-medium text-text-primary mb-1"
            >
              Message personnalise
            </label>
            <textarea
              id="devis-email-message"
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
