import { Code2 } from "lucide-react";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function ApiPubliquePage() {
  return (
    <ComingSoon
      title="API publique v1"
      description="Une API REST documentee pour integrer OptiFlow a vos partenaires (mutuelles, plateformes tiers payant, outils comptables)."
      icon={Code2}
      releaseEstimate="T3 2026"
      features={[
        "Tokens API par tenant avec scopes granulaires (read:clients, write:devis, etc.)",
        "Documentation Swagger interactive avec exemples de code (curl, Python, Node)",
        "Rate limiting personnalise par token (1k req/min par defaut)",
        "Webhooks bidirectionnels pour notifier vos systemes",
        "SDK officiel Python et TypeScript",
      ]}
    />
  );
}
