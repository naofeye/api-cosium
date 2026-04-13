"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ChevronLeft, ChevronRight, Eye, X } from "lucide-react";

import { cn } from "@/lib/utils";
import { useSidebar } from "@/lib/sidebar-context";
import { useTenant } from "@/lib/tenant-context";

import { navGroups, networkAdminItem, settingsItems } from "./sidebar/navConfig";
import { SidebarGroup } from "./sidebar/SidebarGroup";
import { isActive, SidebarItem } from "./sidebar/SidebarItem";
import { useCollapsedGroups } from "./sidebar/useCollapsedGroups";

function SidebarHeader({
  showLabel,
  collapsed,
  mobileOpen,
  onToggle,
  onLinkClick,
}: {
  showLabel: boolean;
  collapsed: boolean;
  mobileOpen: boolean;
  onToggle: () => void;
  onLinkClick: () => void;
}) {
  const toggleLabel = mobileOpen ? "Fermer le menu" : collapsed ? "Agrandir le menu" : "Reduire le menu";

  return (
    <div className="flex h-16 items-center justify-between px-4 border-b border-white/10">
      {showLabel ? (
        <Link href="/actions" className="flex items-center gap-2.5 group" onClick={onLinkClick}>
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
        onClick={onToggle}
        className="rounded-lg p-1.5 hover:bg-white/10 transition-all duration-200"
        aria-label={toggleLabel}
        title={toggleLabel}
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
  );
}

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  const { collapsedGroups, toggleGroup } = useCollapsedGroups();
  const { isMultiTenant } = useTenant();
  const { mobileOpen, closeMobile } = useSidebar();

  const showLabel = mobileOpen || !collapsed;
  const handleLinkClick = () => closeMobile();
  const handleToggleSidebar = () => {
    if (mobileOpen) closeMobile();
    else setCollapsed((v) => !v);
  };

  const sidebarContent = (
    <>
      <SidebarHeader
        showLabel={showLabel}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={handleToggleSidebar}
        onLinkClick={handleLinkClick}
      />

      <nav className="mt-2 flex-1 overflow-y-auto px-2">
        {navGroups.map((group) => (
          <SidebarGroup
            key={group.key}
            group={group}
            pathname={pathname}
            showLabel={showLabel}
            collapsedGroups={collapsedGroups}
            onToggleGroup={toggleGroup}
            onLinkClick={handleLinkClick}
          />
        ))}

        {showLabel ? (
          <div className="mx-3 my-3 border-t border-white/10" />
        ) : (
          <div className="my-2" />
        )}

        {settingsItems.map((item) => (
          <SidebarItem
            key={item.href}
            item={item}
            active={isActive(pathname, item.href)}
            showLabel={showLabel}
            onClick={handleLinkClick}
          />
        ))}

        {isMultiTenant && (
          <>
            {showLabel && <div className="mx-3 my-3 border-t border-white/10" />}
            <SidebarItem
              item={networkAdminItem}
              active={isActive(pathname, networkAdminItem.href)}
              showLabel={showLabel}
              onClick={handleLinkClick}
            />
          </>
        )}
      </nav>
    </>
  );

  return (
    <>
      {/* Desktop */}
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

      {/* Backdrop mobile */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden transition-opacity duration-200"
          onClick={closeMobile}
          aria-hidden="true"
        />
      )}

      {/* Mobile slide-in */}
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
