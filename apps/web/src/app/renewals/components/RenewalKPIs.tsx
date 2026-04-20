import { KPICard } from "@/components/ui/KPICard";
import { formatMoney } from "@/lib/format";
import { Target, TrendingUp, Euro, Send } from "lucide-react";

export interface RenewalDashboard {
  total_opportunities: number;
  high_score_count: number;
  avg_months_since_purchase: number;
  estimated_revenue: number;
  campaigns_sent: number;
  campaigns_this_month: number;
  top_opportunities: unknown[];
}

interface RenewalKPIsProps {
  dashboard: RenewalDashboard;
}

export function RenewalKPIs({ dashboard }: RenewalKPIsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <KPICard icon={Target} label="Opportunites detectees" value={dashboard.total_opportunities} color="primary" />
      <KPICard
        icon={TrendingUp}
        label="Fort potentiel (score >= 70)"
        value={dashboard.high_score_count}
        color="success"
      />
      <KPICard
        icon={Euro}
        label="CA potentiel estime"
        value={formatMoney(dashboard.estimated_revenue)}
        color="warning"
      />
      <KPICard icon={Send} label="Campagnes ce mois" value={dashboard.campaigns_this_month} color="info" />
    </div>
  );
}
