"use client";

import type { Tab, TabDef } from "./ClientTabsTypes";

interface ClientTabsNavProps {
  tabs: TabDef[];
  activeTab: Tab;
  onTabChange: (tab: Tab) => void;
}

export function ClientTabsNav({ tabs, activeTab, onTabChange }: ClientTabsNavProps) {
  return (
    <div className="border-b border-border mb-6">
      <div className="flex gap-0 overflow-x-auto" role="tablist" aria-label="Sections du client">
        {tabs.map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={activeTab === t.key}
            aria-controls={`tabpanel-${t.key}`}
            id={`tab-${t.key}`}
            onClick={() => onTabChange(t.key)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${activeTab === t.key ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"}`}
          >
            {t.label}
            {t.count !== undefined && t.count > 0 && (
              <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{t.count}</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
