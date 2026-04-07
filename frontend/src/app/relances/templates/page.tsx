"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { reminderTemplateSchema, type ReminderTemplateFormData } from "@/lib/schemas/reminder";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { fetchJson } from "@/lib/api";
import { Plus, Eye, Mail, MessageSquare, FileText, Phone } from "lucide-react";

interface Template {
  id: number;
  name: string;
  channel: string;
  payer_type: string;
  subject: string | null;
  body: string;
  is_default: boolean;
}

const CHANNEL_ICONS: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  courrier: FileText,
  telephone: Phone,
};

export default function TemplatesPage() {
  const { data: templates, error: tplErr, isLoading, mutate } = useSWR<Template[]>("/reminders/templates");
  const [showForm, setShowForm] = useState(false);
  const [preview, setPreview] = useState<Template | null>(null);
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting, isValid },
  } = useForm<ReminderTemplateFormData>({
    resolver: zodResolver(reminderTemplateSchema),
    mode: "onChange",
    defaultValues: {
      name: "",
      channel: "email",
      payer_type: "client",
      subject: "",
      body: "",
      is_default: false,
    },
  });

  const watchChannel = watch("channel");

  const onSubmit = async (data: ReminderTemplateFormData) => {
    try {
      await fetchJson("/reminders/templates", {
        method: "POST",
        body: JSON.stringify({
          name: data.name,
          channel: data.channel,
          payer_type: data.payer_type,
          subject: data.subject || null,
          body: data.body,
          is_default: data.is_default,
        }),
      });
      setShowForm(false);
      reset();
      mutate();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    }
  };

  const previewBody = (tpl: Template) => {
    let rendered = tpl.body;
    rendered = rendered.replace(/\{\{client_name\}\}/g, "Marie Dupont");
    rendered = rendered.replace(/\{\{montant\}\}/g, "250,00");
    rendered = rendered.replace(/\{\{jours_retard\}\}/g, "14");
    rendered = rendered.replace(/\{\{facture_numero\}\}/g, "F-2026-0001");
    rendered = rendered.replace(/\{\{date_echeance\}\}/g, "15/03/2026");
    return rendered;
  };

  const displayError = tplErr?.message ?? error;

  if (isLoading)
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Templates" }]}>
        <LoadingState text="Chargement des templates..." />
      </PageLayout>
    );
  if (displayError)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Templates" }]}>
        <ErrorState
          message={displayError}
          onRetry={() => {
            setError(null);
            mutate();
          }}
        />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Templates de relance"
      description="Modeles de messages pour les relances"
      breadcrumb={[{ label: "Relances", href: "/relances" }, { label: "Templates" }]}
      actions={
        <Button onClick={() => setShowForm(!showForm)}>
          <Plus className="h-4 w-4 mr-1" /> Nouveau template
        </Button>
      }
    >
      {showForm && (
        <form
          onSubmit={handleSubmit(onSubmit)}
          className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6"
        >
          <h3 className="text-lg font-semibold text-text-primary mb-4">Nouveau template</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom *</label>
              <input
                type="text"
                {...register("name")}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
              {errors.name && <p className="mt-1 text-xs text-danger">{errors.name.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Canal</label>
              <select {...register("channel")} className="w-full rounded-lg border border-border px-3 py-2 text-sm">
                <option value="email">Email</option>
                <option value="sms">SMS</option>
                <option value="courrier">Courrier</option>
              </select>
              {errors.channel && <p className="mt-1 text-xs text-danger">{errors.channel.message}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Type payeur</label>
              <select {...register("payer_type")} className="w-full rounded-lg border border-border px-3 py-2 text-sm">
                <option value="client">Client</option>
                <option value="mutuelle">Mutuelle</option>
                <option value="secu">Securite sociale</option>
              </select>
              {errors.payer_type && <p className="mt-1 text-xs text-danger">{errors.payer_type.message}</p>}
            </div>
          </div>
          {watchChannel === "email" && (
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Objet</label>
              <input
                type="text"
                {...register("subject")}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Rappel de paiement - Facture {{facture_numero}}"
              />
              {errors.subject && <p className="mt-1 text-xs text-danger">{errors.subject.message}</p>}
            </div>
          )}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Corps du message *</label>
            <textarea
              {...register("body")}
              rows={6}
              className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              placeholder="Bonjour {{client_name}},&#10;&#10;Relance pour {{montant}} EUR..."
            />
            {errors.body && <p className="mt-1 text-xs text-danger">{errors.body.message}</p>}
            <p className="text-xs text-text-secondary mt-1">
              Variables disponibles : {"{{client_name}}"}, {"{{montant}}"}, {"{{jours_retard}}"}, {"{{facture_numero}}"}
              , {"{{date_echeance}}"}
            </p>
          </div>
          <div className="flex items-center gap-4 mb-4">
            <label htmlFor="is_default" className="flex items-center gap-2 text-sm">
              <input type="checkbox" id="is_default" {...register("is_default")} />
              Template par defaut
            </label>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={!isValid || isSubmitting}>
              {isSubmitting ? "Creation..." : "Creer"}
            </Button>
            <Button type="button" variant="outline" onClick={() => setShowForm(false)}>
              Annuler
            </Button>
          </div>
        </form>
      )}

      {preview && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-blue-800">Apercu : {preview.name}</h4>
            <button onClick={() => setPreview(null)} className="text-xs text-blue-600 hover:underline">
              Fermer
            </button>
          </div>
          {preview.subject && <p className="text-sm font-medium text-blue-900 mb-2">Objet : {preview.subject}</p>}
          <div className="bg-white rounded-lg p-4 text-sm whitespace-pre-wrap">{previewBody(preview)}</div>
        </div>
      )}

      {(templates?.length ?? 0) === 0 ? (
        <EmptyState title="Aucun template" description="Creez vos templates de relance personnalises." />
      ) : (
        <div className="space-y-3">
          {(templates ?? []).map((tpl) => {
            const Icon = CHANNEL_ICONS[tpl.channel] || Mail;
            return (
              <div
                key={tpl.id}
                className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4"
              >
                <div className="rounded-lg bg-gray-100 p-2.5">
                  <Icon className="h-5 w-5 text-text-secondary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <h4 className="text-sm font-semibold text-text-primary">{tpl.name}</h4>
                    <StatusBadge status={tpl.payer_type} />
                    <span className="text-xs text-text-secondary capitalize">{tpl.channel}</span>
                    {tpl.is_default && (
                      <span className="text-xs text-primary bg-blue-50 rounded-full px-2 py-0.5">Par defaut</span>
                    )}
                  </div>
                  {tpl.subject && <p className="text-xs text-text-secondary truncate">Objet : {tpl.subject}</p>}
                </div>
                <Button variant="outline" onClick={() => setPreview(preview?.id === tpl.id ? null : tpl)}>
                  <Eye className="h-4 w-4 mr-1" /> Apercu
                </Button>
              </div>
            );
          })}
        </div>
      )}
    </PageLayout>
  );
}
