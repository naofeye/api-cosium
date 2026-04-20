import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";
import { Euro, TrendingUp, CheckCircle, AlertCircle, Users, FileText, ClipboardList, CreditCard, RotateCcw } from "lucide-react";

interface KPIComparison {
  ca_total_delta: number | null;
  montant_encaisse_delta: number | null;
  reste_a_encaisser_delta: number | null;
  taux_recouvrement_delta: number | null;
  clients_delta: number | null;
  factures_delta: number | null;
}

export interface DashboardKPIsProps {
  financial: {
    ca_total: number;
    montant_encaisse: number;
    reste_a_encaisser: number;
    taux_recouvrement: number;
  };
  cosiumCounts: {
    total_clients: number;
    total_rdv: number;
    total_prescriptions: number;
    total_payments: number;
  } | null;
  cosium: {
    invoice_count: number;
    quote_count: number;
    credit_note_count: number;
    total_facture_cosium: number;
    total_devis_cosium: number;
    total_avoirs_cosium: number;
  } | null;
  comparison?: KPIComparison | null;
}

function toTrend(delta: number | null | undefined, label?: string): { value: number; label?: string } | undefined {
  if (delta === null || delta === undefined) return undefined;
  return { value: delta, label: label ?? "vs semaine derniere" };
}

export function DashboardKPIs({ financial, cosiumCounts, cosium, comparison }: DashboardKPIsProps) {
  return (
    <div className="space-y-4 mb-8">
      {/* Row 1: Financial KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={Euro}
          label="CA total"
          value={formatMoney(financial.ca_total)}
          color="primary"
          trend={toTrend(comparison?.ca_total_delta, "vs semaine derniere")}
        />
        <KPICard
          icon={CheckCircle}
          label="Encaisse"
          value={formatMoney(financial.montant_encaisse)}
          color="success"
          trend={toTrend(comparison?.montant_encaisse_delta, "vs semaine derniere")}
        />
        <KPICard
          icon={AlertCircle}
          label="Impayes"
          value={formatMoney(financial.reste_a_encaisser)}
          color={financial.reste_a_encaisser > 0 ? "danger" : "success"}
          trend={toTrend(comparison?.reste_a_encaisser_delta, "vs semaine derniere")}
        />
        <KPICard
          icon={TrendingUp}
          label="Taux recouvrement"
          value={`${financial.taux_recouvrement} %`}
          color={financial.taux_recouvrement > 80 ? "success" : "warning"}
          trend={toTrend(comparison?.taux_recouvrement_delta, "vs semaine derniere")}
        />
      </div>

      {/* Row 2: Volume KPIs — factures, devis, avoirs separated */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <KPICard
          icon={Users}
          label="Clients"
          value={cosiumCounts ? cosiumCounts.total_clients.toLocaleString("fr-FR") : "0"}
          color="primary"
          trend={toTrend(comparison?.clients_delta, "vs semaine derniere")}
        />
        <KPICard
          icon={FileText}
          label="Factures"
          value={cosium ? `${cosium.invoice_count.toLocaleString("fr-FR")} (${formatMoney(cosium.total_facture_cosium)})` : "0"}
          color="primary"
          trend={toTrend(comparison?.factures_delta, "vs semaine derniere")}
        />
        <KPICard
          icon={ClipboardList}
          label="Devis"
          value={cosium ? `${cosium.quote_count.toLocaleString("fr-FR")} (${formatMoney(cosium.total_devis_cosium)})` : "0"}
          color="primary"
        />
        <KPICard
          icon={RotateCcw}
          label="Avoirs"
          value={cosium ? `${cosium.credit_note_count.toLocaleString("fr-FR")} (${formatMoney(cosium.total_avoirs_cosium)})` : "0"}
          color="warning"
        />
        <KPICard
          icon={CreditCard}
          label="Paiements"
          value={cosiumCounts ? cosiumCounts.total_payments.toLocaleString("fr-FR") : "0"}
          color="primary"
        />
      </div>
    </div>
  );
}
