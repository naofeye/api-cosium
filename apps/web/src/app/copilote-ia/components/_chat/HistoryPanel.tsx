"use client";

import useSWR from "swr";
import { Trash2, History, Loader2 } from "lucide-react";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { useState } from "react";
import type { ChatMessage } from "../MessageBubble";

interface ConversationItem {
  id: number;
  title: string;
  mode: string;
  case_id: number | null;
  created_at: string;
  updated_at: string;
}

interface ConversationDetail extends ConversationItem {
  messages: {
    id: number;
    role: string;
    content: string;
    created_at: string;
  }[];
}

interface HistoryPanelProps {
  open: boolean;
  onClose: () => void;
  onLoadConversation: (messages: ChatMessage[], conversationId: number) => void;
}

export function HistoryPanel({ open, onClose, onLoadConversation }: HistoryPanelProps) {
  const { toast } = useToast();
  const { data, error, isLoading, mutate } = useSWR<ConversationItem[]>(
    open ? "/ai/conversations" : null,
  );
  const [loadingId, setLoadingId] = useState<number | null>(null);

  if (!open) return null;

  const handleLoad = async (id: number) => {
    setLoadingId(id);
    try {
      const detail = await fetchJson<ConversationDetail>(`/ai/conversations/${id}`);
      const msgs: ChatMessage[] = detail.messages
        .filter((m) => m.role !== "error")
        .map((m) => ({
          id: `saved-${m.id}`,
          role: m.role === "assistant" ? "assistant" : "user",
          text: m.content,
        }));
      onLoadConversation(msgs, detail.id);
      onClose();
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors du chargement.",
        "error",
      );
    } finally {
      setLoadingId(null);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Supprimer definitivement cette conversation ?")) return;
    try {
      await fetchJson(`/ai/conversations/${id}`, { method: "DELETE" });
      toast("Conversation supprimee.", "success");
      mutate();
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors de la suppression.",
        "error",
      );
    }
  };

  return (
    <div className="absolute inset-y-0 right-0 z-20 w-80 max-w-[90vw] border-l border-border bg-bg-card shadow-xl flex flex-col">
      <div className="flex items-center justify-between border-b border-border px-4 py-3 bg-gray-50">
        <div className="flex items-center gap-2">
          <History className="h-4 w-4 text-text-secondary" />
          <h3 className="text-sm font-semibold text-text-primary">Historique</h3>
        </div>
        <button
          onClick={onClose}
          className="rounded p-1 hover:bg-gray-200"
          aria-label="Fermer l'historique"
        >
          <span aria-hidden="true">&times;</span>
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {isLoading && (
          <div className="flex items-center justify-center py-8 text-text-secondary">
            <Loader2 className="h-4 w-4 animate-spin mr-2" /> Chargement...
          </div>
        )}
        {error && (
          <div className="p-4 text-sm text-red-600">
            Erreur : {error instanceof Error ? error.message : "inconnue"}
          </div>
        )}
        {!isLoading && data && data.length === 0 && (
          <div className="p-4 text-sm text-text-secondary text-center">
            Aucune conversation sauvegardee.
          </div>
        )}
        {!isLoading && data && data.length > 0 && (
          <ul className="divide-y divide-border">
            {data.map((conv) => (
              <li key={conv.id}>
                <button
                  type="button"
                  onClick={() => handleLoad(conv.id)}
                  disabled={loadingId !== null}
                  className="w-full text-left p-3 hover:bg-gray-50 dark:hover:bg-gray-800 flex items-start justify-between gap-2 disabled:opacity-50"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-primary truncate">
                      {conv.title}
                    </p>
                    <p className="text-xs text-text-secondary mt-0.5">
                      {conv.mode}
                      {conv.case_id ? ` · Dossier #${conv.case_id}` : ""}
                      {" · "}
                      {new Date(conv.updated_at).toLocaleDateString("fr-FR")}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={(e) => handleDelete(conv.id, e)}
                    className="shrink-0 rounded p-1 text-text-secondary hover:bg-red-100 hover:text-red-600"
                    aria-label="Supprimer la conversation"
                    title="Supprimer"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
