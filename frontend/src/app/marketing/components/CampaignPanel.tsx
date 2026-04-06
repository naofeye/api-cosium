"use client";

import { useMemo, useState } from "react";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Plus, Send, BarChart3, Mail, FileText, Eye } from "lucide-react";
import type { Segment } from "./SegmentPanel";

export interface Campaign {
  id: number;
  name: string;
  segment_id: number;
  channel: string;
  subject: string | null;
  status: string;
  sent_at: string | null;
  created_at: string;
  segment_name: string | null;
}

const CAMPAIGN_TEMPLATES = [
  {
    name: "Rappel renouvellement",
    subject: "Il est temps de renouveler vos lunettes",
    template: "Bonjour {{client_name}},\n\nVotre dernier equipement optique date de plus de 2 ans. C'est le moment ideal pour un bilan de vue et decouvrir nos nouvelles collections.\n\nPrenez rendez-vous des maintenant !\n\nCordialement,\nVotre opticien",
  },
  {
    name: "Offre promotionnelle",
    subject: "Offre speciale : -20% sur les solaires",
    template: "Bonjour {{client_name}},\n\nProfitez de notre offre exceptionnelle : -20% sur toute la collection solaire jusqu'a la fin du mois.\n\nPassez en magasin ou contactez-nous pour en savoir plus.\n\nA bientot !",
  },
  {
    name: "Nouveaute collection",
    subject: "Decouvrez notre nouvelle collection",
    template: "Bonjour {{client_name}},\n\nNous avons le plaisir de vous presenter notre nouvelle collection printemps-ete. Des montures tendance et des verres de derniere generation vous attendent.\n\nVenez les decouvrir en magasin !\n\nCordialement",
  },
];

interface CampaignPanelProps {
  campaigns: Campaign[];
  segments: Segment[];
  showForm: boolean;
  onToggleForm: () => void;
  campName: string;
  onCampNameChange: (v: string) => void;
  campSegId: number | "";
  onCampSegIdChange: (v: number | "") => void;
  campSubject: string;
  onCampSubjectChange: (v: string) => void;
  campTemplate: string;
  onCampTemplateChange: (v: string) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onSend: (campId: number) => void;
}

export function CampaignPanel({
  campaigns,
  segments,
  showForm,
  onToggleForm,
  campName,
  onCampNameChange,
  campSegId,
  onCampSegIdChange,
  campSubject,
  onCampSubjectChange,
  campTemplate,
  onCampTemplateChange,
  submitting,
  onSubmit,
  onSend,
}: CampaignPanelProps) {
  const [showTemplates, setShowTemplates] = useState(false);

  // Campaign statistics summary
  const stats = useMemo(() => {
    const total = campaigns.length;
    const sent = campaigns.filter((c) => c.status === "sent").length;
    const draft = campaigns.filter((c) => c.status === "draft").length;
    return { total, sent, draft };
  }, [campaigns]);

  // Recipient count preview
  const selectedSegment = segments.find((s) => s.id === campSegId);

  const applyTemplate = (tpl: typeof CAMPAIGN_TEMPLATES[number]) => {
    onCampNameChange(tpl.name);
    onCampSubjectChange(tpl.subject);
    onCampTemplateChange(tpl.template);
    setShowTemplates(false);
  };

  return (
    <>
      {/* Campaign statistics */}
      {campaigns.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <BarChart3 className="h-4 w-4 text-blue-500" aria-hidden="true" />
              <span className="text-xs text-text-secondary">Total campagnes</span>
            </div>
            <p className="text-2xl font-bold text-text-primary">{stats.total}</p>
          </div>
          <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <Send className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              <span className="text-xs text-text-secondary">Envoyees</span>
            </div>
            <p className="text-2xl font-bold text-emerald-600">{stats.sent}</p>
          </div>
          <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <FileText className="h-4 w-4 text-gray-400" aria-hidden="true" />
              <span className="text-xs text-text-secondary">Brouillons</span>
            </div>
            <p className="text-2xl font-bold text-gray-600">{stats.draft}</p>
          </div>
        </div>
      )}

      <div className="flex justify-end gap-2 mb-4">
        <Button variant="outline" onClick={() => setShowTemplates(!showTemplates)}>
          <FileText className="h-4 w-4 mr-1" /> Templates
        </Button>
        <Button onClick={onToggleForm}>
          <Plus className="h-4 w-4 mr-1" /> Nouvelle campagne
        </Button>
      </div>

      {/* Campaign templates section */}
      {showTemplates && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold mb-4">Modeles de campagne</h3>
          <p className="text-sm text-text-secondary mb-4">
            Selectionnez un modele pour pre-remplir le formulaire de creation.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {CAMPAIGN_TEMPLATES.map((tpl, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-border p-4 hover:border-primary hover:bg-blue-50/30 transition-colors cursor-pointer"
                onClick={() => {
                  applyTemplate(tpl);
                  if (!showForm) onToggleForm();
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    applyTemplate(tpl);
                    if (!showForm) onToggleForm();
                  }
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Mail className="h-4 w-4 text-primary" aria-hidden="true" />
                  <h4 className="text-sm font-semibold">{tpl.name}</h4>
                </div>
                <p className="text-xs text-text-secondary mb-1">{tpl.subject}</p>
                <p className="text-xs text-gray-400 line-clamp-2">{tpl.template.slice(0, 100)}...</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {showForm && (
        <form onSubmit={onSubmit} className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold mb-4">Nouvelle campagne</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom *</label>
              <input
                type="text"
                value={campName}
                onChange={(e) => onCampNameChange(e.target.value)}
                required
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Segment *</label>
              <select
                value={campSegId}
                onChange={(e) => onCampSegIdChange(Number(e.target.value))}
                required
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              >
                <option value="">Selectionner</option>
                {segments.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.member_count} membres)
                  </option>
                ))}
              </select>
              {/* Recipient count preview */}
              {selectedSegment && (
                <div className="mt-2 flex items-center gap-1.5 text-xs text-blue-600 bg-blue-50 rounded-lg px-3 py-1.5">
                  <Eye className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>
                    {selectedSegment.member_count} destinataire{selectedSegment.member_count > 1 ? "s" : ""} dans ce segment
                  </span>
                </div>
              )}
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Objet email</label>
              <input
                type="text"
                value={campSubject}
                onChange={(e) => onCampSubjectChange(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Offre speciale ete"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-1">Template *</label>
              <textarea
                value={campTemplate}
                onChange={(e) => onCampTemplateChange(e.target.value)}
                required
                rows={6}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm font-mono"
                placeholder="Bonjour {{client_name}},&#10;..."
              />
              <p className="text-xs text-text-secondary mt-1">
                Variables : {"{{client_name}}"}, {"{{prenom}}"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creation..." : "Creer la campagne"}
            </Button>
            <Button type="button" variant="outline" onClick={onToggleForm}>
              Annuler
            </Button>
          </div>
        </form>
      )}
      {campaigns.length === 0 ? (
        <EmptyState title="Aucune campagne" description="Creez votre premiere campagne marketing." />
      ) : (
        <div className="space-y-3">
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-semibold">{c.name}</h4>
                  <StatusBadge status={c.status} />
                  <span className="text-xs text-text-secondary">{c.segment_name}</span>
                </div>
                <p className="text-xs text-text-secondary">
                  {c.subject || "Sans objet"} | <DateDisplay date={c.created_at} />
                  {c.sent_at && (
                    <>
                      {" "}
                      | Envoye le <DateDisplay date={c.sent_at} />
                    </>
                  )}
                </p>
              </div>
              {c.status === "draft" && (
                <Button onClick={() => onSend(c.id)}>
                  <Send className="h-4 w-4 mr-1" /> Envoyer
                </Button>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}
