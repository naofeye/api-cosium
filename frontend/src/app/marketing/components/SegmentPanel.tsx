"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Plus, Users } from "lucide-react";

export interface Segment {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
  created_at: string;
}

interface SegmentPanelProps {
  segments: Segment[];
  showForm: boolean;
  onToggleForm: () => void;
  segName: string;
  onSegNameChange: (v: string) => void;
  segDesc: string;
  onSegDescChange: (v: string) => void;
  segHasEmail: boolean;
  onSegHasEmailChange: (v: boolean) => void;
  segCity: string;
  onSegCityChange: (v: string) => void;
  submitting: boolean;
  onSubmit: (e: React.FormEvent) => void;
}

export function SegmentPanel({
  segments,
  showForm,
  onToggleForm,
  segName,
  onSegNameChange,
  segDesc,
  onSegDescChange,
  segHasEmail,
  onSegHasEmailChange,
  segCity,
  onSegCityChange,
  submitting,
  onSubmit,
}: SegmentPanelProps) {
  return (
    <>
      <div className="flex justify-end mb-4">
        <Button onClick={onToggleForm}>
          <Plus className="h-4 w-4 mr-1" /> Nouveau segment
        </Button>
      </div>
      {showForm && (
        <form onSubmit={onSubmit} className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h3 className="text-lg font-semibold mb-4">Nouveau segment</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium mb-1">Nom *</label>
              <input
                type="text"
                value={segName}
                onChange={(e) => onSegNameChange(e.target.value)}
                required
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                type="text"
                value={segDesc}
                onChange={(e) => onSegDescChange(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={segHasEmail} onChange={(e) => onSegHasEmailChange(e.target.checked)} />{" "}
                Avec email
              </label>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Ville</label>
              <input
                type="text"
                value={segCity}
                onChange={(e) => onSegCityChange(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Optionnel"
              />
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
      {segments.length === 0 ? (
        <EmptyState title="Aucun segment" description="Creez votre premier segment de clients." />
      ) : (
        <div className="space-y-3">
          {segments.map((s) => (
            <div
              key={s.id}
              className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4"
            >
              <div className="rounded-lg bg-blue-50 p-2.5">
                <Users className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold">{s.name}</h4>
                <p className="text-xs text-text-secondary">
                  {s.description || "Pas de description"} | {s.member_count} membre(s)
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
