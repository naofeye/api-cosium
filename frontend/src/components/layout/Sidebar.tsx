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
  X,
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
      { href: "/paiements", label: "Paiements", icon: CreditCard },
      { href: "/rapprochement", label: "Rapprochement", icon: ArrowLeftRight },
      { href: "/pec", label: "PEC", icon: Shield },
      { href: "/pec-dashboard", label: "Assistance PEC", icon: ClipboardCheck },
    ],
  },
  {
    key: "cosium",
    label: "Cosium",
    items: [
      { href: "/cosium-factures", label: "Factures Cosium", icon: FileStack },
      { href: "/cosium-paiements", label: "Paiements Cosium", icon: CreditCard },
      { href: "/agenda", label: "Agenda", icon: Calendar },
      { href: "/ordonnances", label: "Ordonnances", icon: FileText },
      { href: "/mutuelles", label: "Mutuelles", icon: Shield },
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
                "flex items-center justify-center rounded-lg p-2.5 text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
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
    <div className="mb-1">
      <button
        onClick={() => onToggleGroup(group.key)}
        className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-gray-500 hover:text-gray-300 transition-colors duration-150"
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
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                  active
                    ? "bg-primary text-white border-l-2 border-white"
                    : "text-gray-400 hover:bg-gray-800 hover:text-white",
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
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
      <div className="flex h-16 items-center justify-between px-4">
        {showLabel && (
          <Link href="/actions" className="text-lg font-bold" onClick={handleLinkClick}>
            OptiFlow AI
          </Link>
        )}
        <button
          onClick={() => {
            if (mobileOpen) {
              closeMobile();
            } else {
              setCollapsed(!collapsed);
            }
          }}
          className="rounded-lg p-1.5 hover:bg-gray-800 transition-colors duration-150"
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
        {showLabel && <div className="mx-3 my-3 border-t border-gray-700" />}
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
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
                !showLabel && "justify-center",
              )}
              title={!showLabel ? item.label : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {showLabel && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Network admin: visible only if multi-tenant */}
        {isMultiTenant && (
          <>
            {showLabel && <div className="mx-3 my-3 border-t border-gray-700" />}
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
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                pathname === networkAdminItem.href || pathname.startsWith(networkAdminItem.href + "/")
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
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
          "fixed inset-y-0 left-0 z-40 hidden lg:flex flex-col bg-bg-sidebar text-text-on-dark transition-all duration-200",
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
          "fixed inset-y-0 left-0 z-50 flex w-72 flex-col bg-bg-sidebar text-text-on-dark transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {sidebarContent}
      </aside>
    </>
  );
}
