"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { Bot, Send } from "lucide-react";

interface TabIAProps {
  caseId: number;
}

export function TabIA({ caseId }: TabIAProps) {
  const [aiQuestion, setAiQuestion] = useState("");
  const [aiResponse, setAiResponse] = useState<string | null>(null);
  const [aiMode, setAiMode] = useState("dossier");
  const [aiLoading, setAiLoading] = useState(false);

  const askAI = async () => {
    if (!aiQuestion.trim() || aiLoading) return;
    setAiLoading(true);
    setAiResponse(null);
    try {
      const resp = await fetchJson<{ response: string }>("/ai/copilot/query", {
        method: "POST",
        body: JSON.stringify({ question: aiQuestion, case_id: caseId, mode: aiMode }),
      });
      setAiResponse(resp.response);
    } catch (err) {
      setAiResponse(err instanceof Error ? err.message : "Erreur IA");
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <Bot className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold text-text-primary">Assistant IA</h3>
      </div>
      <div className="flex gap-3 mb-4">
        <select
          value={aiMode}
          onChange={(e) => setAiMode(e.target.value)}
          className="rounded-lg border border-border px-3 py-2 text-sm"
        >
          <option value="dossier">Copilote Dossier</option>
          <option value="financier">Copilote Financier</option>
          <option value="documentaire">Copilote Documentaire</option>
          <option value="marketing">Copilote Marketing</option>
        </select>
        <input
          type="text"
          value={aiQuestion}
          onChange={(e) => setAiQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && askAI()}
          placeholder="Posez votre question..."
          className="flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
        <Button onClick={askAI} disabled={aiLoading || !aiQuestion.trim()}>
          <Send className="h-4 w-4 mr-1" />
          {aiLoading ? "Analyse..." : "Demander"}
        </Button>
      </div>
      {aiResponse && (
        <div className="rounded-lg bg-gray-50 border border-border p-4 text-sm whitespace-pre-wrap">{aiResponse}</div>
      )}
      {!aiResponse && !aiLoading && (
        <p className="text-sm text-text-secondary text-center py-4">
          Posez une question sur ce dossier. L&apos;IA analysera le contexte complet (client, documents, paiements,
          PEC).
        </p>
      )}
    </div>
  );
}
