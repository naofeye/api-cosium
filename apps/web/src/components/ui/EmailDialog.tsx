"use client";

import { useState, useCallback } from "react";
import { X, Send, Loader2, FileText, CalendarCheck, CreditCard } from "lucide-react";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

interface EmailDialogProps {
  open: boolean;
  onClose: () => void;
  clientId: string | number;
  clientEmail: string;
  clientName: string;
  onSent?: () => void;
}

interface TemplateOption {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  subject: string;
  body: string;
}

const TEMPLATES: TemplateOption[] = [
  {
    label: "Rappel RDV",
    icon: CalendarCheck,
    subject: "Rappel de votre rendez-vous",
    body: "Bonjour,\n\nNous vous rappelons votre prochain rendez-vous dans notre magasin.\n\nN'hesitez pas a nous contacter en cas d'empechement.\n\nCordialement,\nL'equipe OptiFlow",
  },
  {
    label: "Confirmation devis",
    icon: FileText,
    subject: "Confirmation de votre devis",
    body: "Bonjour,\n\nNous vous confirmons la bonne reception de votre devis.\n\nN'hesitez pas a revenir vers nous pour toute question.\n\nCordialement,\nL'equipe OptiFlow",
  },
  {
    label: "Relance paiement",
    icon: CreditCard,
    subject: "Rappel de paiement",
    body: "Bonjour,\n\nNous nous permettons de vous rappeler qu'un reglement est en attente concernant votre dossier.\n\nMerci de prendre contact avec nous a votre convenance.\n\nCordialement,\nL'equipe OptiFlow",
  },
];

export function EmailDialog({
  open,
  onClose,
  clientId,
  clientEmail,
  clientName,
  onSent,
}: EmailDialogProps) {
  const { toast } = useToast();
  const [to, setTo] = useState(clientEmail);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [sending, setSending] = useState(false);

  const applyTemplate = useCallback((tpl: TemplateOption) => {
    setSubject(tpl.subject);
    setBody(tpl.body);
  }, []);

  const handleSend = useCallback(async () => {
    if (sending || !subject.trim() || !body.trim()) return;
    setSending(true);
    try {
      await fetchJson(`/clients/${clientId}/send-email`, {
        method: "POST",
        body: JSON.stringify({ to, subject, body }),
      });
      toast("Email envoye avec succes", "success");
      setSubject("");
      setBody("");
      onSent?.();
      onClose();
    } catch {
      // Global error handler covers this
    } finally {
      setSending(false);
    }
  }, [sending, subject, body, to, clientId, toast, onSent, onClose]);

  if (!open) return null;

  const isValid = to.trim().length > 0 && subject.trim().length > 0 && body.trim().length > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog */}
      <div className="relative z-10 w-full max-w-lg rounded-xl bg-white shadow-xl mx-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <h2 className="text-lg font-semibold text-text-primary">
            Envoyer un email a {clientName}
          </h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-text-secondary hover:bg-gray-100 transition-colors"
            aria-label="Fermer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-4 space-y-4">
          {/* Templates */}
          <div>
            <p className="text-xs font-medium text-text-secondary mb-2">Modeles rapides</p>
            <div className="flex flex-wrap gap-2">
              {TEMPLATES.map((tpl) => {
                const Icon = tpl.icon;
                return (
                  <button
                    key={tpl.label}
                    onClick={() => applyTemplate(tpl)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:bg-gray-50 hover:text-text-primary transition-colors"
                    type="button"
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    {tpl.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* To */}
          <div>
            <label htmlFor="email-to" className="block text-sm font-medium text-text-primary mb-1">
              Destinataire
            </label>
            <input
              id="email-to"
              type="email"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="w-full rounded-lg border border-border bg-gray-50 px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Subject */}
          <div>
            <label htmlFor="email-subject" className="block text-sm font-medium text-text-primary mb-1">
              Objet *
            </label>
            <input
              id="email-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Objet de l'email"
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            />
          </div>

          {/* Body */}
          <div>
            <label htmlFor="email-body" className="block text-sm font-medium text-text-primary mb-1">
              Message *
            </label>
            <textarea
              id="email-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Redigez votre message..."
              rows={6}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary resize-y"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-2 border-t border-border px-6 py-4">
          <button
            onClick={onClose}
            className="rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-gray-50 transition-colors"
            type="button"
          >
            Annuler
          </button>
          <button
            onClick={handleSend}
            disabled={sending || !isValid}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            type="button"
          >
            {sending ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
            {sending ? "Envoi en cours..." : "Envoyer"}
          </button>
        </div>
      </div>
    </div>
  );
}
