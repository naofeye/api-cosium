"use client";

import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";
import { Euro, TrendingUp, CheckCircle, Clock } from "lucide-react";

export interface DashboardKPIsProps {
  financial: {
    ca_total: number;
    montant_encaisse: number;
    reste_a_encaisser: number;
    taux_recouvrement: number;
  };
}

export function DashboardKPIs({ financial }: DashboardKPIsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <KPICard icon={Euro} label="CA total" value={formatMoney(financial.ca_total)} color="primary" />
      <KPICard icon={CheckCircle} label="Encaisse" value={formatMoney(financial.montant_encaisse)} color="success" />
      <KPICard
        icon={Clock}
        label="Reste a encaisser"
        value={formatMoney(financial.reste_a_encaisser)}
        color={financial.reste_a_encaisser > 0 ? "danger" : "success"}
      />
      <KPICard
        icon={TrendingUp}
        label="Taux recouvrement"
        value={`${financial.taux_recouvrement}%`}
        color={financial.taux_recouvrement > 80 ? "success" : "warning"}
      />
    </div>
  );
}
