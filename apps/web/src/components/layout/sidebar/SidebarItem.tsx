import Link from "next/link";
import { cn } from "@/lib/utils";
import type { NavItem } from "./navConfig";

interface Props {
  item: NavItem;
  active: boolean;
  showLabel: boolean;
  onClick: () => void;
  badge?: number;
}

export function SidebarItem({ item, active, showLabel, onClick, badge }: Props) {
  const badgeText = badge && badge > 0 ? (badge > 99 ? "99+" : String(badge)) : null;
  return (
    <Link
      href={item.href}
      onClick={onClick}
      aria-current={active ? "page" : undefined}
      aria-label={!showLabel ? `${item.label}${badgeText ? ` (${badge} actions)` : ""}` : undefined}
      title={!showLabel ? item.label : undefined}
      className={cn(
        "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-200",
        "focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none",
        active
          ? "bg-white/10 text-white border-l-3 border-blue-400 shadow-sm shadow-blue-500/10"
          : "text-gray-400 hover:bg-white/5 hover:text-gray-200",
        !showLabel && "justify-center",
      )}
    >
      <item.icon
        className={cn("h-5 w-5 shrink-0", active && "text-blue-400")}
        aria-hidden="true"
      />
      {showLabel && <span className="flex-1">{item.label}</span>}
      {badgeText && showLabel && (
        <span className="rounded-full bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white tabular-nums shadow-sm shadow-red-500/30">
          {badgeText}
        </span>
      )}
    </Link>
  );
}

export function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(href + "/");
}
