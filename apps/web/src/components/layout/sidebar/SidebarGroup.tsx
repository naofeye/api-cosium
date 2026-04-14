import Link from "next/link";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { isActive, SidebarItem } from "./SidebarItem";
import type { NavGroup } from "./navConfig";

interface Props {
  group: NavGroup;
  pathname: string;
  showLabel: boolean;
  collapsedGroups: Record<string, boolean>;
  onToggleGroup: (key: string) => void;
  onLinkClick: () => void;
  badges?: Record<string, number>;
}

export function SidebarGroup({
  group,
  pathname,
  showLabel,
  collapsedGroups,
  onToggleGroup,
  onLinkClick,
  badges,
}: Props) {
  const hasActiveItem = group.items.some((item) => isActive(pathname, item.href));
  const effectiveCollapsed = (collapsedGroups[group.key] ?? false) && !hasActiveItem;

  // Mode icones-only : on aplatit (pas de header de groupe)
  if (!showLabel) {
    return (
      <>
        {group.items.map((item) => {
          const active = isActive(pathname, item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onLinkClick}
              aria-current={active ? "page" : undefined}
              aria-label={item.label}
              title={item.label}
              className={cn(
                "flex items-center justify-center rounded-lg p-2.5 text-sm font-medium transition-all duration-200",
                "focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
                active
                  ? "bg-white/10 text-blue-400 border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
                  : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
              )}
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
          {group.items.map((item) => (
            <SidebarItem
              key={item.href}
              item={item}
              active={isActive(pathname, item.href)}
              showLabel
              onClick={onLinkClick}
              badge={badges?.[item.href]}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
