"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
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
  ChevronLeft,
  ChevronRight,
  ChevronDown,
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
  X,
  Eye,
  type LucideIcon,
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { useTenant } from "@/lib/tenant-context";
import { useSidebar } from "@/lib/sidebar-context";

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

interface NavGroup {
  key: string;
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
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

// Settings items (below separator)
const settingsItems: NavItem[] = [
  { href: "/settings/billing", label: "Facturation", icon: CreditCard },
  { href: "/settings/ai-usage", label: "Consommation IA", icon: Brain },
  { href: "/settings/erp", label: "Connexion ERP", icon: Database },
];

const networkAdminItem: NavItem = { href: "/admin/network", label: "Admin Reseau", icon: Building2 };

const STORAGE_KEY = "optiflow-sidebar-collapsed-groups";

function loadCollapsedGroups(): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? (JSON.parse(stored) as Record<string, boolean>) : {};
  } catch {
    return {};
  }
}

function saveCollapsedGroups(state: Record<string, boolean>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore storage errors
  }
}

function SidebarGroupComponent({
  group,
  pathname,
  showLabel,
  collapsedGroups,
  onToggleGroup,
  onLinkClick,
}: {
  group: NavGroup;
  pathname: string;
  showLabel: boolean;
  collapsedGroups: Record<string, boolean>;
  onToggleGroup: (key: string) => void;
  onLinkClick: () => void;
}) {
  const isCollapsed = collapsedGroups[group.key] ?? false;
  const hasActiveItem = group.items.some(
    (item) => pathname === item.href || pathname.startsWith(item.href + "/"),
  );

  // Auto-open if active item is inside and group is collapsed
  const effectiveCollapsed = isCollapsed && !hasActiveItem;

  if (!showLabel) {
    // Icon-only mode: flatten, no group headers
    return (
      <>
        {group.items.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onLinkClick}
              aria-current={active ? "page" : undefined}
              aria-label={item.label}
              className={cn(
                "flex items-center justify-center rounded-lg p-2.5 text-sm font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-white/10 text-blue-400 border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
              )}
              title={item.label}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
            </Link>
          );
        })}
      </>
    );
  }

  return (
    <div className="mb-1 mt-3">
      <button
        onClick={() => onToggleGroup(group.key)}
        className="flex w-full items-center justify-between px-3 py-2 text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-gray-300 transition-all duration-200 border-b border-white/5 pb-2"
        aria-expanded={!effectiveCollapsed}
        aria-label={`${effectiveCollapsed ? "Ouvrir" : "Fermer"} la section ${group.label}`}
      >
        <span>{group.label}</span>
        <ChevronDown
          className={cn(
            "h-3.5 w-3.5 transition-transform duration-200",
            effectiveCollapsed && "-rotate-90",
          )}
          aria-hidden="true"
        />
      </button>
      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          effectiveCollapsed ? "max-h-0 opacity-0" : "max-h-96 opacity-100",
        )}
      >
        <div className="space-y-0.5 mt-0.5">
          {group.items.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={onLinkClick}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                  active
                    ? "bg-white/10 text-white border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
                    : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
                )}
              >
                <item.icon className={cn("h-5 w-5 shrink-0", active && "text-blue-400")} aria-hidden="true" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const { isMultiTenant } = useTenant();
  const { mobileOpen, closeMobile } = useSidebar();

  useEffect(() => {
    setCollapsedGroups(loadCollapsedGroups());
  }, []);

  const handleToggleGroup = useCallback((key: string) => {
    setCollapsedGroups((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      saveCollapsedGroups(next);
      return next;
    });
  }, []);

  const handleLinkClick = () => {
    closeMobile();
  };

  const showLabel = mobileOpen || !collapsed;

  const sidebarContent = (
    <>
      <div className="flex h-16 items-center justify-between px-4 border-b border-white/10">
        {showLabel ? (
          <Link href="/actions" className="flex items-center gap-2.5 group" onClick={handleLinkClick}>
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 transition-transform duration-200 group-hover:scale-105">
              <Eye className="h-4.5 w-4.5 text-white" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-white">OptiFlow AI</span>
              <span className="text-[10px] text-gray-500 font-medium -mt-0.5">Gestion Optique</span>
            </div>
          </Link>
        ) : (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/25 mx-auto">
            <Eye className="h-4.5 w-4.5 text-white" />
          </div>
        )}
        <button
          onClick={() => {
            if (mobileOpen) {
              closeMobile();
            } else {
              setCollapsed(!collapsed);
            }
          }}
          className="rounded-lg p-1.5 hover:bg-white/10 transition-all duration-200"
          aria-label={mobileOpen ? "Fermer le menu" : collapsed ? "Agrandir le menu" : "Reduire le menu"}
          title={mobileOpen ? "Fermer le menu" : collapsed ? "Agrandir le menu" : "Reduire le menu"}
        >
          {mobileOpen ? (
            <X className="h-5 w-5" />
          ) : collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>

      <nav className="mt-2 flex-1 overflow-y-auto px-2">
        {navGroups.map((group) => (
          <SidebarGroupComponent
            key={group.key}
            group={group}
            pathname={pathname}
            showLabel={showLabel}
            collapsedGroups={collapsedGroups}
            onToggleGroup={handleToggleGroup}
            onLinkClick={handleLinkClick}
          />
        ))}

        {/* Settings section */}
        {showLabel && <div className="mx-3 my-3 border-t border-white/10" />}
        {!showLabel && <div className="my-2" />}
        {settingsItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleLinkClick}
              aria-current={active ? "page" : undefined}
              aria-label={!showLabel ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-white/10 text-white border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
                !showLabel && "justify-center",
              )}
              title={!showLabel ? item.label : undefined}
            >
              <item.icon className={cn("h-5 w-5 shrink-0", active && "text-blue-400")} aria-hidden="true" />
              {showLabel && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Network admin: visible only if multi-tenant */}
        {isMultiTenant && (
          <>
            {showLabel && <div className="mx-3 my-3 border-t border-white/10" />}
            <Link
              href={networkAdminItem.href}
              onClick={handleLinkClick}
              aria-current={
                pathname === networkAdminItem.href || pathname.startsWith(networkAdminItem.href + "/")
                  ? "page"
                  : undefined
              }
              aria-label={!showLabel ? networkAdminItem.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                pathname === networkAdminItem.href || pathname.startsWith(networkAdminItem.href + "/")
                  ? "bg-white/10 text-white border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
                !showLabel && "justify-center",
              )}
              title={!showLabel ? networkAdminItem.label : undefined}
            >
              <networkAdminItem.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {showLabel && <span>{networkAdminItem.label}</span>}
            </Link>
          </>
        )}
      </nav>
    </>
  );

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        role="navigation"
        aria-label="Menu principal"
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden lg:flex flex-col bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 text-text-on-dark transition-all duration-200",
          collapsed ? "w-16" : "w-64",
        )}
      >
        {sidebarContent}
      </aside>

      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity duration-200"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar (slide-in overlay) */}
      <aside
        role="navigation"
        aria-label="Menu principal"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-gradient-to-b from-gray-900 via-gray-900 to-gray-950 text-text-on-dark transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
