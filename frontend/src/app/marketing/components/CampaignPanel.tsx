"use client";

import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { Plus, Send } from "lucide-react";
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
  return (
    <>
      <div className="flex justify-end mb-4">
        <Button onClick={onToggleForm}>
          <Plus className="h-4 w-4 mr-1" /> Nouvelle campagne
        </Button>
      </div>
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
                rows={4}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Bonjour {{client_name}},&#10;..."
              />
              <p className="text-xs text-text-secondary mt-1">
                Variables : {"{{client_name}}"}, {"{{prenom}}"}
              </p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Creation..." : "Creer"}
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
