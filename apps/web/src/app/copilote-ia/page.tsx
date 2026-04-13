import { Brain } from "lucide-react";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function CopiloteIAPage() {
  return (
    <ComingSoon
      title="Copilote IA"
      description="Un assistant intelligent integre a OptiFlow qui repond a vos questions sur vos clients, prepare vos PEC et suggere les meilleures actions commerciales."
      icon={Brain}
      releaseEstimate="T2 2026"
      features={[
        "Recherche conversationnelle (Ctrl+K) : retrouvez n'importe quelle info en langage naturel",
        "Suggestions automatiques de relances client adaptees au contexte",
        "Resume intelligent des dossiers complexes en 3 lignes",
        "Detection automatique des anomalies dans les factures",
        "Pre-remplissage IA des formulaires PEC depuis les ordonnances scannees",
      ]}
    />
  );
}
