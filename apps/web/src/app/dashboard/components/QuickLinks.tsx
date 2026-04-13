import Link from "next/link";
import { Calendar, Eye, RefreshCw, type LucideIcon } from "lucide-react";
import type { DashboardData } from "../types";

interface LinkTileProps {
  href: string;
  icon: LucideIcon;
  title: string;
  subtitle: string;
}

function LinkTile({ href, icon: Icon, title, subtitle }: LinkTileProps) {
  return (
    <Link
      href={href}
      className="flex items-center gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm hover:border-primary transition-colors"
    >
      <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
      <div>
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        <p className="text-xs text-text-secondary">{subtitle}</p>
      </div>
    </Link>
  );
}

interface Props {
  cosium: DashboardData["cosium"];
  cosiumCounts: DashboardData["cosium_counts"];
}

export function QuickLinks({ cosium, cosiumCounts }: Props) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <LinkTile
        href="/agenda"
        icon={Calendar}
        title="Agenda"
        subtitle={cosiumCounts ? `${cosiumCounts.total_rdv.toLocaleString("fr-FR")} rendez-vous` : "Voir le planning"}
      />
      <LinkTile
        href="/ordonnances"
        icon={Eye}
        title="Ordonnances"
        subtitle={cosiumCounts ? `${cosiumCounts.total_prescriptions.toLocaleString("fr-FR")} prescriptions` : "Voir les ordonnances"}
      />
      <LinkTile
        href="/cosium-factures"
        icon={RefreshCw}
        title="Factures Cosium"
        subtitle={cosium ? `${cosium.invoice_count.toLocaleString("fr-FR")} factures` : "Voir les factures"}
      />
    </div>
  );
}
