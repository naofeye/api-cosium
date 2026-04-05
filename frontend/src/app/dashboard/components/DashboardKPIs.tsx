"use client";

import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";
import { Euro, TrendingUp, CheckCircle, AlertCircle, Users, FileText, ClipboardList, CreditCard } from "lucide-react";

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
  } | null;
}

export function DashboardKPIs({ financial, cosiumCounts, cosium }: DashboardKPIsProps) {
  return (
    <div className="space-y-4 mb-8">
      {/* Row 1: Financial KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard icon={Euro} label="CA total" value={formatMoney(financial.ca_total)} color="primary" />
        <KPICard icon={CheckCircle} label="Encaisse" value={formatMoney(financial.montant_encaisse)} color="success" />
        <KPICard
          icon={AlertCircle}
          label="Impayes"
          value={formatMoney(financial.reste_a_encaisser)}
          color={financial.reste_a_encaisser > 0 ? "danger" : "success"}
        />
        <KPICard
          icon={TrendingUp}
          label="Taux recouvrement"
          value={`${financial.taux_recouvrement} %`}
          color={financial.taux_recouvrement > 80 ? "success" : "warning"}
        />
      </div>

      {/* Row 2: Volume KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard
          icon={Users}
          label="Clients"
          value={cosiumCounts ? cosiumCounts.total_clients.toLocaleString("fr-FR") : "0"}
          color="primary"
        />
        <KPICard
          icon={FileText}
          label="Factures"
          value={cosium ? cosium.invoice_count.toLocaleString("fr-FR") : "0"}
          color="primary"
        />
        <KPICard
          icon={ClipboardList}
          label="Devis"
          value={cosium ? cosium.quote_count.toLocaleString("fr-FR") : "0"}
          color="primary"
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
