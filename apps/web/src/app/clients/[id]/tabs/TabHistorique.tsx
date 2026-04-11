"use client";

import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Plus, PhoneCall, Mail, MessageSquare, Eye, Pencil, Calendar } from "lucide-react";

interface Interaction {
  id: number;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_at: string;
}

interface TabHistoriqueProps {
  interactions: Interaction[];
  showForm: boolean;
  onShowForm: (show: boolean) => void;
  intType: string;
  onIntTypeChange: (value: string) => void;
  intDir: string;
  onIntDirChange: (value: string) => void;
  intSubj: string;
  onIntSubjChange: (value: string) => void;
  intBody: string;
  onIntBodyChange: (value: string) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

const TYPE_ICONS: Record<string, typeof PhoneCall> = {
  appel: PhoneCall,
  email: Mail,
  sms: MessageSquare,
  visite: Eye,
  note: Pencil,
  tache: Calendar,
};

export function TabHistorique({
  interactions,
  showForm,
  onShowForm,
  intType,
  onIntTypeChange,
  intDir,
  onIntDirChange,
  intSubj,
  onIntSubjChange,
  intBody,
  onIntBodyChange,
  submitting,
  onSubmit,
}: TabHistoriqueProps) {
  return (
    <div className="space-y-4">
      {showForm && (
        <form onSubmit={onSubmit} className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h4 className="text-sm font-semibold mb-3">Nouvelle interaction</h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
            <select
              value={intType}
              onChange={(e) => onIntTypeChange(e.target.value)}
              className="rounded-lg border border-border px-3 py-2 text-sm"
            >
              <option value="note">Note</option>
              <option value="appel">Appel</option>
              <option value="email">Email</option>
              <option value="sms">SMS</option>
              <option value="visite">Visite</option>
              <option value="tache">Tache</option>
            </select>
            <select
              value={intDir}
              onChange={(e) => onIntDirChange(e.target.value)}
              className="rounded-lg border border-border px-3 py-2 text-sm"
            >
              <option value="interne">Interne</option>
              <option value="entrant">Entrant</option>
              <option value="sortant">Sortant</option>
            </select>
            <input
              type="text"
              value={intSubj}
              onChange={(e) => onIntSubjChange(e.target.value)}
              placeholder="Sujet *"
              required
              className="rounded-lg border border-border px-3 py-2 text-sm"
            />
          </div>
          <textarea
            value={intBody}
            onChange={(e) => onIntBodyChange(e.target.value)}
            placeholder="Contenu (optionnel)"
            rows={3}
            className="w-full rounded-lg border border-border px-3 py-2 text-sm mb-3"
          />
          <div className="flex gap-2">
            <Button type="submit" disabled={submitting}>
              {submitting ? "Ajout..." : "Ajouter"}
            </Button>
            <Button type="button" variant="outline" onClick={() => onShowForm(false)}>
              Annuler
            </Button>
          </div>
        </form>
      )}
      {!showForm && (
        <div className="flex justify-end">
          <Button variant="outline" onClick={() => onShowForm(true)}>
            <Plus className="h-4 w-4 mr-1" /> Ajouter
          </Button>
        </div>
      )}
      <div className="rounded-xl border border-border bg-bg-card shadow-sm">
        {interactions.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Aucune interaction" description="L'historique des echanges apparaitra ici." />
          </div>
        ) : (
          <div className="divide-y divide-border">
            {interactions.map((i) => {
              const Icon = TYPE_ICONS[i.type] || Pencil;
              return (
                <div key={i.id} className="flex items-start gap-3 px-5 py-3">
                  <div className="rounded-full bg-gray-100 p-1.5 mt-0.5">
                    <Icon className="h-4 w-4 text-text-secondary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{i.subject}</span>
                      <span className="text-xs text-text-secondary capitalize">{i.type}</span>
                      <span className="text-xs text-text-secondary">({i.direction})</span>
                    </div>
                    {i.content && <p className="text-xs text-text-secondary mt-0.5 line-clamp-2">{i.content}</p>}
                    <p className="text-xs text-text-secondary mt-0.5">
                      <DateDisplay date={i.created_at} />
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
