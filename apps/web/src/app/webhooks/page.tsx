import { Webhook } from "lucide-react";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function WebhooksPage() {
  return (
    <ComingSoon
      title="Webhooks"
      description="Connectez OptiFlow a vos outils metier en temps reel : recevez des notifications HTTP a chaque evenement (nouveau client, devis signe, paiement recu)."
      icon={Webhook}
      releaseEstimate="T3 2026"
      features={[
        "Configuration de plusieurs URLs cibles avec filtres par type d'evenement",
        "Signature HMAC pour verifier l'authenticite des payloads",
        "Retry automatique avec backoff exponentiel en cas d'echec",
        "Historique des deliveries avec replay manuel",
        "Documentation OpenAPI generee pour chaque webhook",
      ]}
    />
  );
}
