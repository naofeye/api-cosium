import { AlertTriangle, CheckCircle, ListChecks, Send } from "lucide-react";
import { KPICard } from "@/components/ui/KPICard";

export function PecKpiCards({ counts }: { counts: Record<string, number> }) {
  const totalAll =
    (counts.en_preparation ?? 0) + (counts.prete ?? 0) + (counts.soumise ?? 0);

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <KPICard icon={ListChecks} label="Total preparations" value={totalAll} color="primary" />
      <KPICard icon={CheckCircle} label="Pretes" value={counts.prete ?? 0} color="success" />
      <KPICard icon={AlertTriangle} label="En preparation" value={counts.en_preparation ?? 0} color="warning" />
      <KPICard icon={Send} label="Soumises" value={counts.soumise ?? 0} color="info" />
    </div>
  );
}
