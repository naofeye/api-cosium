import Link from "next/link";
import { AlertCircle, ClipboardCheck, Search, Settings, type LucideIcon } from "lucide-react";

interface ActionTileProps {
  href?: string;
  onClick?: () => void;
  icon: LucideIcon;
  iconClass?: string;
  title: string;
  subtitle: string;
}

function ActionTile({ href, onClick, icon: Icon, iconClass = "text-primary", title, subtitle }: ActionTileProps) {
  const className = "flex flex-col items-center gap-3 rounded-xl border border-border bg-bg-card p-5 shadow-sm hover:border-primary hover:shadow-md transition-all text-center group";
  const inner = (
    <>
      <Icon className={`h-6 w-6 ${iconClass}`} aria-hidden="true" />
      <span className="text-sm font-semibold text-text-primary">{title}</span>
      <span className="text-xs text-text-secondary">{subtitle}</span>
    </>
  );
  if (href) {
    return <Link href={href} className={className}>{inner}</Link>;
  }
  return <button onClick={onClick} className={className}>{inner}</button>;
}

function triggerSearch() {
  const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true });
  document.dispatchEvent(event);
}

export function QuickActions() {
  return (
    <div className="mb-8">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wide mb-3">
        Actions rapides
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
        <ActionTile
          href="/pec-dashboard"
          icon={ClipboardCheck}
          title="Nouvelle PEC"
          subtitle="Preparer une prise en charge"
        />
        <ActionTile
          onClick={triggerSearch}
          icon={Search}
          title="Rechercher un client"
          subtitle="Ctrl+K pour la recherche"
        />
        <ActionTile
          href="/cosium-factures?status=impayee"
          icon={AlertCircle}
          iconClass="text-danger"
          title="Voir les impayes"
          subtitle="Factures en attente de paiement"
        />
        <ActionTile
          href="/admin"
          icon={Settings}
          title="Sync Cosium"
          subtitle="Synchroniser les donnees"
        />
      </div>
    </div>
  );
}
