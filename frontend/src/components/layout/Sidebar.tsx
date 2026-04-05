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
  HelpCircle,
  FileStack,
  Calendar,
  Stethoscope,
  BarChart3,
  X,
} from "lucide-react";
import { useState } from "react";
import { useTenant } from "@/lib/tenant-context";
import { useSidebar } from "@/lib/sidebar-context";

const navItems = [
  { href: "/actions", label: "Actions", icon: Zap },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/statistiques", label: "Statistiques", icon: BarChart3 },
  { href: "/cases", label: "Dossiers", icon: FolderOpen },
  { href: "/clients", label: "Clients", icon: Users },
  { href: "/devis", label: "Devis", icon: FileText },
  { href: "/factures", label: "Factures", icon: Receipt },
  { href: "/cosium-factures", label: "Factures Cosium", icon: FileStack },
  { href: "/cosium-paiements", label: "Paiements Cosium", icon: CreditCard },
  { href: "/agenda", label: "Agenda", icon: Calendar },
  { href: "/ordonnances", label: "Ordonnances", icon: FileText },
  { href: "/mutuelles", label: "Mutuelles", icon: Shield },
  { href: "/prescripteurs", label: "Prescripteurs", icon: Stethoscope },
  { href: "/pec", label: "PEC", icon: Shield },
  { href: "/paiements", label: "Paiements", icon: CreditCard },
  { href: "/rapprochement", label: "Rapprochement", icon: ArrowLeftRight },
  { href: "/relances", label: "Relances", icon: Send },
  { href: "/marketing", label: "Marketing", icon: Megaphone },
  { href: "/renewals", label: "Renouvellements", icon: RefreshCw },
  { href: "/admin", label: "Admin", icon: Settings },
  { href: "/aide", label: "Aide", icon: HelpCircle },
];

// Items settings
const settingsItems = [
  { href: "/settings/billing", label: "Facturation", icon: CreditCard },
  { href: "/settings/ai-usage", label: "Consommation IA", icon: Brain },
  { href: "/settings/erp", label: "Connexion ERP", icon: Database },
];

// Item "Administration Reseau" visible uniquement si multi-tenant
const networkAdminItem = { href: "/admin/network", label: "Admin Reseau", icon: Building2 };

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { isMultiTenant } = useTenant();
  const { mobileOpen, closeMobile } = useSidebar();

  const handleLinkClick = () => {
    // Close mobile sidebar when navigating
    closeMobile();
  };

  const sidebarContent = (
    <>
      <div className="flex h-16 items-center justify-between px-4">
        {!collapsed && (
          <Link href="/actions" className="text-lg font-bold" onClick={handleLinkClick}>
            OptiFlow AI
          </Link>
        )}
        {/* Desktop: collapse toggle. Mobile: close button */}
        <button
          onClick={() => {
            if (mobileOpen) {
              closeMobile();
            } else {
              setCollapsed(!collapsed);
            }
          }}
          className="rounded-lg p-1.5 hover:bg-gray-800"
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

      <nav className="mt-4 flex-1 space-y-1 overflow-y-auto px-2">
        {navItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const showLabel = mobileOpen || !collapsed;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleLinkClick}
              aria-current={active ? "page" : undefined}
              aria-label={!showLabel ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
              )}
              title={!showLabel ? item.label : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {showLabel && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Section Parametres */}
        {(mobileOpen || !collapsed) && <div className="mx-3 my-3 border-t border-gray-700" />}
        {settingsItems.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const showLabel = mobileOpen || !collapsed;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleLinkClick}
              aria-current={active ? "page" : undefined}
              aria-label={!showLabel ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
              )}
              title={!showLabel ? item.label : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {showLabel && <span>{item.label}</span>}
            </Link>
          );
        })}

        {/* Administration Reseau : visible uniquement si multi-tenant */}
        {isMultiTenant && (
          <>
            {(mobileOpen || !collapsed) && <div className="mx-3 my-3 border-t border-gray-700" />}
            <Link
              href={networkAdminItem.href}
              onClick={handleLinkClick}
              aria-current={
                pathname === networkAdminItem.href || pathname.startsWith(networkAdminItem.href + "/")
                  ? "page"
                  : undefined
              }
              aria-label={!mobileOpen && collapsed ? networkAdminItem.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                pathname === networkAdminItem.href || pathname.startsWith(networkAdminItem.href + "/")
                  ? "bg-primary text-white border-l-2 border-white"
                  : "text-gray-400 hover:bg-gray-800 hover:text-white",
              )}
              title={!mobileOpen && collapsed ? networkAdminItem.label : undefined}
            >
              <networkAdminItem.icon className="h-5 w-5 shrink-0" aria-hidden="true" />
              {(mobileOpen || !collapsed) && <span>{networkAdminItem.label}</span>}
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
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
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
