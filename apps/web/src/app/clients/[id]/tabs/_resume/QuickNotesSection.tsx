import { useCallback, useState } from "react";
import { Loader2, Pencil, Send } from "lucide-react";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { fetchJson } from "@/lib/api";
import type { Interaction } from "./types";

export function QuickNotesSection({
  clientId,
  interactions,
  onNoteAdded,
}: {
  clientId: string | number;
  interactions: Interaction[];
  onNoteAdded?: () => void;
}) {
  const [noteText, setNoteText] = useState("");
  const [noteSending, setNoteSending] = useState(false);

  const handleAddNote = useCallback(async () => {
    const trimmed = noteText.trim();
    if (!trimmed || noteSending) return;
    setNoteSending(true);
    try {
      await fetchJson("/interactions", {
        method: "POST",
        body: JSON.stringify({
          client_id: Number(clientId),
          type: "note",
          direction: "interne",
          subject: trimmed,
        }),
      });
      setNoteText("");
      onNoteAdded?.();
    } catch {
      // Error toast is handled globally by fetchJson
    } finally {
      setNoteSending(false);
    }
  }, [noteText, noteSending, clientId, onNoteAdded]);

  const handleNoteKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleAddNote();
      }
    },
    [handleAddNote],
  );

  const notes = interactions.filter((i) => i.type === "note");

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <Pencil className="h-5 w-5 text-primary" aria-hidden="true" />
        Notes rapides
      </h3>

      <div className="flex items-center gap-2 mb-4">
        <input
          type="text"
          value={noteText}
          onChange={(e) => setNoteText(e.target.value)}
          onKeyDown={handleNoteKeyDown}
          placeholder="Ajouter une note rapide..."
          disabled={noteSending}
          className="flex-1 rounded-lg border border-border bg-white px-3 py-2 text-sm placeholder:text-text-secondary focus:border-primary focus:ring-1 focus:ring-primary outline-none disabled:opacity-50"
        />
        <button
          onClick={handleAddNote}
          disabled={noteSending || !noteText.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Envoyer la note"
        >
          {noteSending ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
          Ajouter
        </button>
      </div>

      {notes.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-4">
          Aucune note pour le moment.
        </p>
      ) : (
        <div className="space-y-2">
          {notes.slice(0, 10).map((n) => (
            <div
              key={n.id}
              className="flex items-start gap-3 rounded-lg bg-gray-50 p-3 text-sm"
            >
              <Pencil
                className="h-4 w-4 text-text-secondary mt-0.5 shrink-0"
                aria-hidden="true"
              />
              <div className="min-w-0 flex-1">
                <p className="text-text-primary">{n.subject}</p>
                <p className="text-xs text-text-secondary mt-0.5">
                  <DateDisplay date={n.created_at} />
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
