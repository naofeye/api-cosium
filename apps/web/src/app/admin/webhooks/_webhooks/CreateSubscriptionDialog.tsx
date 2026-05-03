"use client";

import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";

interface Props {
  allowedEvents: string[];
  onClose: () => void;
  onCreated: (name: string, secret: string) => void;
}

export function CreateSubscriptionDialog({ allowedEvents, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("https://");
  const [description, setDescription] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (event: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(event)) next.delete(event);
      else next.add(event);
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (selected.size === 0) {
      setError("Selectionnez au moins un evenement.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await fetchJson<{ name: string; secret: string }>(
        "/webhooks/subscriptions",
        {
          method: "POST",
          body: JSON.stringify({
            name: name.trim(),
            url: url.trim(),
            event_types: Array.from(selected),
            description: description.trim() || undefined,
          }),
        },
      );
      onCreated(result.name, result.secret);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Echec de la creation.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Nouvelle subscription webhook"
    >
      <div className="bg-white rounded-xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6">
          <h2 className="text-lg font-semibold mb-4">Nouvelle subscription webhook</h2>

          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Nom *</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                placeholder="Ex: Notif comptabilite"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">URL HTTPS *</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
                placeholder="https://exemple.com/optiflow-hooks"
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 font-mono text-sm"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Description (optionnel)
              </label>
              <input
                type="text"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                maxLength={500}
                className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700 mb-2 block">
                Evenements ecoutes * ({selected.size} selectionne{selected.size > 1 ? "s" : ""})
              </label>
              <div className="grid grid-cols-2 gap-2 max-h-60 overflow-y-auto border border-gray-200 rounded-lg p-3">
                {allowedEvents.map((event) => (
                  <label
                    key={event}
                    className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-50 rounded px-2 py-1"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(event)}
                      onChange={() => toggle(event)}
                    />
                    <span className="font-mono text-xs">{event}</span>
                  </label>
                ))}
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
          </div>

          <div className="mt-6 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              Annuler
            </Button>
            <Button type="submit" disabled={submitting || !name || !url || selected.size === 0}>
              {submitting ? "Creation..." : "Creer la subscription"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
