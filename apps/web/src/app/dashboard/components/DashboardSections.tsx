import { formatMoney } from "@/lib/format";
import { FolderOpen, ShoppingCart, Megaphone } from "lucide-react";

interface OperationalData {
  dossiers_en_cours: number;
  dossiers_complets: number;
  taux_completude: number;
  pieces_manquantes: number;
}

interface CommercialData {
  devis_en_cours: number;
  devis_signes: number;
  taux_conversion: number;
  panier_moyen: number;
  ca_par_mois: { mois: string; ca: number }[];
}

interface MarketingData {
  campagnes_total: number;
  campagnes_envoyees: number;
  messages_envoyes: number;
}

interface DashboardSectionsProps {
  operational: OperationalData;
  commercial: CommercialData;
  marketing: MarketingData;
}

export function DashboardSections({ operational, commercial, marketing }: DashboardSectionsProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
      {/* Operationnel */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <FolderOpen className="h-5 w-5" /> Operationnel
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Dossiers en cours</span>
            <span className="font-semibold">{operational.dossiers_en_cours}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Dossiers complets</span>
            <span className="font-semibold text-emerald-700">{operational.dossiers_complets}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Taux completude</span>
            <span
              className={`font-semibold ${operational.taux_completude > 80 ? "text-emerald-700" : "text-amber-700"}`}
            >
              {operational.taux_completude}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Pieces manquantes</span>
            <span
              className={`font-semibold ${operational.pieces_manquantes > 0 ? "text-red-700" : "text-emerald-700"}`}
            >
              {operational.pieces_manquantes}
            </span>
          </div>
        </div>
      </div>

      {/* Commercial */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <ShoppingCart className="h-5 w-5" /> Commercial
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Devis en cours</span>
            <span className="font-semibold">{commercial.devis_en_cours}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Devis signes</span>
            <span className="font-semibold text-emerald-700">{commercial.devis_signes}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Taux conversion</span>
            <span
              className={`font-semibold ${commercial.taux_conversion > 50 ? "text-emerald-700" : "text-amber-700"}`}
            >
              {commercial.taux_conversion}%
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Panier moyen</span>
            <span className="font-semibold">{formatMoney(commercial.panier_moyen)}</span>
          </div>
        </div>
      </div>

      {/* Marketing */}
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Megaphone className="h-5 w-5" /> Marketing
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Campagnes total</span>
            <span className="font-semibold">{marketing.campagnes_total}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Campagnes envoyees</span>
            <span className="font-semibold text-emerald-700">{marketing.campagnes_envoyees}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-secondary">Messages envoyes</span>
            <span className="font-semibold">{marketing.messages_envoyes}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
