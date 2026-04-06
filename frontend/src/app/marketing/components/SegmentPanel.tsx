"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Plus, Users, Target, Tag, X, Mail, MapPin, Phone } from "lucide-react";

export interface Segment {
  id: number;
  name: string;
  description: string | null;
  member_count: number;
  created_at: string;
}

interface FilterTag {
  key: string;
  label: string;
  icon: React.ElementType;
  color: string;
}

const AVAILABLE_FILTERS: FilterTag[] = [
  { key: "has_email", label: "Avec email", icon: Mail, color: "bg-blue-100 text-blue-700 border-blue-200" },
  { key: "has_phone", label: "Avec telephone", icon: Phone, color: "bg-emerald-100 text-emerald-700 border-emerald-200" },
  { key: "city", label: "Par ville", icon: MapPin, color: "bg-purple-100 text-purple-700 border-purple-200" },
];

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
  // Build active filter tags for display
  const activeTags: { key: string; label: string; color: string }[] = [];
  if (segHasEmail) {
    activeTags.push({ key: "has_email", label: "Avec email", color: "bg-blue-100 text-blue-700 border-blue-200" });
  }
  if (segCity.trim()) {
    activeTags.push({ key: "city", label: `Ville : ${segCity}`, color: "bg-purple-100 text-purple-700 border-purple-200" });
  }

  const removeTag = (key: string) => {
    if (key === "has_email") onSegHasEmailChange(false);
    if (key === "city") onSegCityChange("");
  };

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
                placeholder="Ex: Clients avec email a Paris"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description</label>
              <input
                type="text"
                value={segDesc}
                onChange={(e) => onSegDescChange(e.target.value)}
                className="w-full rounded-lg border border-border px-3 py-2 text-sm"
                placeholder="Description optionnelle"
              />
            </div>
          </div>

          {/* Visual filter builder */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              <Tag className="h-4 w-4 inline mr-1" aria-hidden="true" />
              Filtres du segment
            </label>

            {/* Active filter tags */}
            {activeTags.length > 0 && (
              <div className="flex flex-wrap gap-2 mb-3">
                {activeTags.map((tag) => (
                  <span
                    key={tag.key}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border ${tag.color}`}
                  >
                    {tag.label}
                    <button
                      type="button"
                      onClick={() => removeTag(tag.key)}
                      className="ml-0.5 hover:opacity-70"
                      aria-label={`Retirer le filtre ${tag.label}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Filter selector buttons */}
            <div className="rounded-lg border border-dashed border-gray-300 p-4 bg-gray-50/50">
              <p className="text-xs text-text-secondary mb-3">Cliquez pour ajouter des filtres :</p>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_FILTERS.map((filter) => {
                  const isActive =
                    (filter.key === "has_email" && segHasEmail) ||
                    (filter.key === "city" && segCity.trim() !== "");
                  return (
                    <button
                      key={filter.key}
                      type="button"
                      onClick={() => {
                        if (filter.key === "has_email") onSegHasEmailChange(!segHasEmail);
                        if (filter.key === "has_phone") {
                          /* future filter */
                        }
                        if (filter.key === "city") {
                          if (!segCity.trim()) onSegCityChange(" ");
                        }
                      }}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                        isActive
                          ? filter.color
                          : "bg-white text-gray-600 border-gray-200 hover:border-gray-300 hover:bg-gray-50"
                      }`}
                    >
                      <filter.icon className="h-3.5 w-3.5" aria-hidden="true" />
                      {filter.label}
                    </button>
                  );
                })}
              </div>

              {/* City input if city filter is active */}
              {(segCity !== "" || activeTags.some((t) => t.key === "city")) && (
                <div className="mt-3">
                  <input
                    type="text"
                    value={segCity.trim()}
                    onChange={(e) => onSegCityChange(e.target.value)}
                    className="w-full max-w-xs rounded-lg border border-border px-3 py-1.5 text-sm"
                    placeholder="Saisir une ville (ex: Paris)"
                    autoFocus
                  />
                </div>
              )}
            </div>

            {activeTags.length === 0 && (
              <p className="text-xs text-amber-600 mt-2">
                Le segment doit avoir au moins un filtre.
              </p>
            )}
          </div>

          <div className="flex gap-2">
            <Button type="submit" disabled={submitting || activeTags.length === 0}>
              {submitting ? "Creation..." : "Creer le segment"}
            </Button>
            <Button type="button" variant="outline" onClick={onToggleForm}>
              Annuler
            </Button>
          </div>
        </form>
      )}
      {segments.length === 0 ? (
        <EmptyState
          title="Aucun segment"
          description="Creez un segment pour cibler vos campagnes marketing."
          icon={Target}
          action={<Button onClick={onToggleForm}><Plus className="h-4 w-4 mr-1" /> Creer un segment</Button>}
        />
      ) : (
        <div className="space-y-3">
          {segments.map((s) => (
            <div
              key={s.id}
              className="rounded-xl border border-border bg-bg-card p-5 shadow-sm flex items-center gap-4"
            >
              <div className="rounded-lg bg-blue-50 p-2.5">
                <Users className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-semibold">{s.name}</h4>
                <p className="text-xs text-text-secondary">
                  {s.description || "Pas de description"} | {s.member_count} membre{s.member_count > 1 ? "s" : ""}
                </p>
              </div>
              <span className="text-sm font-semibold text-primary tabular-nums">
                {s.member_count}
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
