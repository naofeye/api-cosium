import {
  LayoutDashboard,
  FolderOpen,
  Users,
  Zap,
  FileText,
  Receipt,
  Shield,
  CreditCard,
  ArrowLeftRight,
  Send,
  Megaphone,
  RefreshCw,
  Settings,
  Building2,
  Brain,
  Database,
  HelpCircle,
  FileStack,
  Calendar,
  Stethoscope,
  BarChart3,
  ClipboardCheck,
  Bell,
  Package,
  FolderDown,
  Briefcase,
  RotateCcw,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export interface NavGroup {
  key: string;
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    key: "pilotage",
    label: "Pilotage",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
      { href: "/statistiques", label: "Statistiques", icon: BarChart3 },
      { href: "/actions", label: "Actions", icon: Zap },
    ],
  },
  {
    key: "clients",
    label: "Clients & Dossiers",
    items: [
      { href: "/clients", label: "Clients", icon: Users },
      { href: "/cases", label: "Dossiers", icon: FolderOpen },
      { href: "/prescripteurs", label: "Prescripteurs", icon: Stethoscope },
    ],
  },
  {
    key: "finance",
    label: "Finance",
    items: [
      { href: "/devis", label: "Devis", icon: FileText },
      { href: "/factures", label: "Factures", icon: Receipt },
      { href: "/cosium-factures", label: "Factures Cosium", icon: FileStack },
      { href: "/avoirs", label: "Avoirs", icon: RotateCcw },
      { href: "/paiements", label: "Paiements", icon: CreditCard },
      { href: "/rapprochement", label: "Rapprochement", icon: ArrowLeftRight },
      { href: "/rapprochement-cosium", label: "Rapprochement Cosium", icon: ArrowLeftRight },
      { href: "/pec", label: "PEC", icon: Shield },
      { href: "/pec-dashboard", label: "Assistance PEC", icon: ClipboardCheck },
    ],
  },
  {
    key: "cosium",
    label: "Cosium",
    items: [
      { href: "/cosium-paiements", label: "Paiements Cosium", icon: CreditCard },
      { href: "/agenda", label: "Agenda", icon: Calendar },
      { href: "/ordonnances", label: "Ordonnances", icon: FileText },
      { href: "/mutuelles", label: "Mutuelles", icon: Shield },
      { href: "/produits", label: "Produits", icon: Package },
      { href: "/documents-cosium", label: "Documents", icon: FolderDown },
    ],
  },
  {
    key: "operations-batch",
    label: "Groupes marketing",
    items: [
      { href: "/operations-batch", label: "Groupes marketing", icon: Briefcase },
    ],
  },
  {
    key: "marketing",
    label: "Marketing",
    items: [
      { href: "/marketing", label: "Marketing", icon: Megaphone },
      { href: "/relances", label: "Relances", icon: Send },
      { href: "/renewals", label: "Renouvellements", icon: RefreshCw },
    ],
  },
  {
    key: "admin",
    label: "Administration",
    items: [
      { href: "/admin", label: "Admin", icon: Settings },
      { href: "/notifications", label: "Notifications", icon: Bell },
      { href: "/aide", label: "Aide", icon: HelpCircle },
    ],
  },
];

export const settingsItems: NavItem[] = [
  { href: "/settings/billing", label: "Facturation", icon: CreditCard },
  { href: "/settings/ai-usage", label: "Consommation IA", icon: Brain },
  { href: "/settings/erp", label: "Connexion ERP", icon: Database },
];

export const networkAdminItem: NavItem = {
  href: "/admin/network",
  label: "Admin Reseau",
  icon: Building2,
};
