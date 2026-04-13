import { Smartphone } from "lucide-react";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function MobilePage() {
  return (
    <ComingSoon
      title="Application mobile"
      description="OptiFlow dans votre poche : consultez vos KPIs, validez vos devis et gerez vos relances depuis votre smartphone (iOS et Android)."
      icon={Smartphone}
      releaseEstimate="T4 2026"
      features={[
        "Notifications push pour les paiements recus et PEC validees",
        "Scan rapide de l'ordonnance et de la carte mutuelle",
        "Validation de devis en mobilite (signature electronique)",
        "Mode hors-ligne pour consulter les fiches client",
        "Authentification biometrique (Face ID, Touch ID)",
      ]}
    />
  );
}
