"use client";

import { Send, Trash2, History, Save } from "lucide-react";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { API_BASE } from "@/lib/config";
import { fetchJson } from "@/lib/api";
import { csrfHeaders } from "@/lib/csrf";
import { useToast } from "@/components/ui/Toast";
import { Select } from "@/components/ui/Select";
import { Button } from "@/components/ui/Button";
import { MessageBubble, type ChatMessage } from "./MessageBubble";
import { EmptyChat } from "./_chat/EmptyChat";
import { HistoryPanel } from "./_chat/HistoryPanel";
import { MODE_OPTIONS, MODE_PLACEHOLDERS, type CopilotMode } from "./_chat/modes";
import { parseSseFrames } from "./_chat/sseParser";

export function ChatInterface() {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<CopilotMode>("dossier");
  const [isStreaming, setIsStreaming] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [savedConversationId, setSavedConversationId] = useState<number | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const messageCount = messages.length;
  const placeholder = useMemo(() => MODE_PLACEHOLDERS[mode], [mode]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const updateMessage = useCallback(
    (id: string, updater: (prev: ChatMessage) => ChatMessage) => {
      setMessages((current) =>
        current.map((m) => (m.id === id ? updater(m) : m)),
      );
    },
    [],
  );

  const handleSubmit = useCallback(
    async (e?: FormEvent) => {
      e?.preventDefault();
      const question = input.trim();
      if (!question || isStreaming) return;

      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        text: question,
      };
      const assistantId = `a-${Date.now()}`;
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: "assistant",
        text: "",
        isStreaming: true,
      };
      setMessages((current) => [...current, userMsg, assistantMsg]);
      setInput("");
      setIsStreaming(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const response = await fetch(`${API_BASE}/ai/copilot/stream`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", ...csrfHeaders("POST") },
          body: JSON.stringify({ question, mode }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          throw new Error(`Erreur API ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let receivedAnyChunk = false;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const { events, rest } = parseSseFrames(buffer);
          buffer = rest;

          for (const event of events) {
            if (event.type === "chunk") {
              const text = (event.data.text as string) ?? "";
              receivedAnyChunk = true;
              updateMessage(assistantId, (prev) => ({
                ...prev,
                text: prev.text + text,
              }));
            } else if (event.type === "done") {
              updateMessage(assistantId, (prev) => ({
                ...prev,
                isStreaming: false,
              }));
            } else if (event.type === "error") {
              const msg = (event.data.error as string) ?? "Erreur IA inconnue.";
              updateMessage(assistantId, (prev) => ({
                ...prev,
                role: "error",
                text: msg,
                isStreaming: false,
              }));
              receivedAnyChunk = true;
            }
          }
        }

        if (!receivedAnyChunk) {
          updateMessage(assistantId, (prev) => ({
            ...prev,
            text: "L'assistant n'a renvoyé aucune réponse. Réessayez dans un instant.",
            role: "error",
            isStreaming: false,
          }));
        }
      } catch (err) {
        const aborted = err instanceof DOMException && err.name === "AbortError";
        if (!aborted) {
          const message =
            err instanceof Error
              ? err.message
              : "Une erreur est survenue lors de la communication avec l'assistant.";
          updateMessage(assistantId, (prev) => ({
            ...prev,
            role: "error",
            text: message,
            isStreaming: false,
          }));
          toast(message, "error");
        } else {
          updateMessage(assistantId, (prev) => ({
            ...prev,
            isStreaming: false,
            text: prev.text || "Génération interrompue.",
          }));
        }
      } finally {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [input, isStreaming, mode, toast, updateMessage],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void handleSubmit();
      }
    },
    [handleSubmit],
  );

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleClear = useCallback(() => {
    if (isStreaming) {
      abortRef.current?.abort();
    }
    setMessages([]);
    setSavedConversationId(null);
  }, [isStreaming]);

  const handleLoadConversation = useCallback(
    (loadedMessages: ChatMessage[], conversationId: number) => {
      setMessages(loadedMessages);
      setSavedConversationId(conversationId);
    },
    [],
  );

  const handleSaveConversation = useCallback(async () => {
    // Cherche la derniere paire user/assistant pour la sauver via l'API
    // (qui re-execute Claude — c'est volontaire pour avoir l'historique en BDD).
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    if (!lastUser) {
      toast("Pas de question utilisateur a sauvegarder.", "warning");
      return;
    }
    setIsSaving(true);
    try {
      const result = await fetchJson<{ conversation_id: number; answer: string }>(
        `/ai/conversations/append`,
        {
          method: "POST",
          body: JSON.stringify({
            question: lastUser.text,
            conversation_id: savedConversationId,
            mode,
            case_id: null,
          }),
        },
      );
      setSavedConversationId(result.conversation_id);
      toast("Conversation sauvegardee dans l'historique.", "success");
    } catch (err) {
      toast(
        err instanceof Error ? err.message : "Erreur lors de la sauvegarde.",
        "error",
      );
    } finally {
      setIsSaving(false);
    }
  }, [messages, savedConversationId, mode, toast]);

  return (
    <div className="relative flex flex-col h-[calc(100vh-220px)] min-h-[480px] bg-white rounded-xl border border-border shadow-sm overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-gray-50">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <label htmlFor="copilot-mode" className="text-sm font-medium text-text-primary whitespace-nowrap">
            Mode :
          </label>
          <Select
            id="copilot-mode"
            options={MODE_OPTIONS as unknown as { value: string; label: string }[]}
            value={mode}
            onChange={(e) => setMode(e.target.value as CopilotMode)}
            disabled={isStreaming}
            className="max-w-md"
            aria-label="Sélectionner le mode du copilote"
          />
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setHistoryOpen(true)}
          aria-label="Voir l'historique des conversations"
          title="Historique"
        >
          <History className="w-4 h-4" />
          <span className="hidden sm:inline">Historique</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleSaveConversation}
          disabled={isSaving || isStreaming || messageCount === 0}
          aria-label="Sauvegarder la conversation"
          title={savedConversationId ? "Mettre a jour la conversation sauvee" : "Sauvegarder la conversation"}
        >
          <Save className="w-4 h-4" />
          <span className="hidden sm:inline">{isSaving ? "..." : "Sauver"}</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          disabled={messageCount === 0}
          aria-label="Effacer la conversation"
        >
          <Trash2 className="w-4 h-4" />
          <span className="hidden sm:inline">Effacer</span>
        </Button>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
        {messageCount === 0 ? (
          <EmptyChat mode={mode} />
        ) : (
          messages.map((m) => <MessageBubble key={m.id} message={m} />)
        )}
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-border bg-white p-3 sm:p-4"
      >
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            rows={2}
            className="flex-1 resize-none rounded-lg border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/30 focus:border-blue-500 disabled:bg-gray-50 disabled:text-gray-400"
            disabled={isStreaming}
            aria-label="Votre question"
          />
          {isStreaming ? (
            <Button
              type="button"
              variant="outline"
              onClick={handleStop}
              aria-label="Interrompre la génération"
            >
              Stop
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={!input.trim()}
              aria-label="Envoyer la question"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Envoyer</span>
            </Button>
          )}
        </div>
        <p className="mt-2 text-xs text-text-secondary">
          Entrée pour envoyer · Maj+Entrée pour un saut de ligne · Cliquez Sauver pour persister.
        </p>
      </form>

      <HistoryPanel
        open={historyOpen}
        onClose={() => setHistoryOpen(false)}
        onLoadConversation={handleLoadConversation}
      />
    </div>
  );
}
