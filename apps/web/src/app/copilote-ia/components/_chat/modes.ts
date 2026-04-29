export type CopilotMode = "dossier" | "financier" | "documentaire" | "marketing";

export const MODE_OPTIONS = [
  { value: "dossier", label: "Dossier — analyser un dossier client" },
  { value: "financier", label: "Financier — paiements & relances" },
  { value: "documentaire", label: "Documentaire — aide Cosium" },
  { value: "marketing", label: "Marketing — segments & campagnes" },
] as const;

export const MODE_PLACEHOLDERS: Record<CopilotMode, string> = {
  dossier: "Ex: Quels sont les points d'attention de mon dossier en cours ?",
  financier: "Ex: Quels clients ont des paiements en retard de plus de 30 jours ?",
  documentaire: "Ex: Comment paramétrer une remise automatique dans Cosium ?",
  marketing: "Ex: Suggère un segment client pour une campagne renouvellement.",
};
