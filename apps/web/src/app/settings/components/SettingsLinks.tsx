import { CreditCard, Brain, Database } from "lucide-react";
import Link from "next/link";

const settingsLinks = [
  {
    href: "/settings/billing",
    label: "Facturation et abonnement",
    description: "Plan actuel, historique des factures",
    icon: CreditCard,
  },
  {
    href: "/settings/ai-usage",
    label: "Consommation IA",
    description: "Usage du copilote, quotas, historique",
    icon: Brain,
  },
  {
    href: "/settings/erp",
    label: "Connexion ERP",
    description: "Statut Cosium, synchronisation, configuration",
    icon: Database,
  },
];

export function SettingsLinks() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      {settingsLinks.map((link) => (
        <Link
          key={link.href}
          href={link.href}
          className="flex items-start gap-4 rounded-xl border border-border bg-bg-card p-5 shadow-sm hover:border-primary hover:shadow-md transition-all"
        >
          <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 p-2.5">
            <link.icon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-text-primary">{link.label}</h3>
            <p className="text-xs text-text-secondary mt-0.5">{link.description}</p>
          </div>
        </Link>
      ))}
    </div>
  );
}
