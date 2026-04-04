"use client";

import { Building2, ChevronDown, Check } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTenant } from "@/lib/tenant-context";

export function TenantSelector() {
  const { tenantId, tenantName, availableTenants, isMultiTenant, switchTenant } = useTenant();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Ne rien afficher si un seul tenant accessible
  if (!isMultiTenant) return null;

  const handleSwitch = async (newTenantId: number) => {
    if (newTenantId === tenantId || switching) return;
    setSwitching(true);
    try {
      await switchTenant(newTenantId);
    } catch {
      setSwitching(false);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        aria-label="Changer de magasin"
        disabled={switching}
      >
        <Building2 className="h-4 w-4 text-gray-500" />
        <span className="max-w-[180px] truncate">{switching ? "Changement..." : (tenantName ?? "Magasin")}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-gray-400 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-1 w-64 rounded-xl border border-gray-200 bg-white shadow-lg z-50">
          <div className="border-b border-gray-100 px-3 py-2">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Magasins disponibles</p>
          </div>
          <div className="max-h-60 overflow-y-auto py-1">
            {availableTenants.map((tenant) => {
              const isActive = tenant.id === tenantId;
              return (
                <button
                  key={tenant.id}
                  onClick={() => handleSwitch(tenant.id)}
                  disabled={isActive || switching}
                  className={`flex w-full items-center gap-3 px-3 py-2.5 text-sm transition-colors ${
                    isActive ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  <Building2 className={`h-4 w-4 shrink-0 ${isActive ? "text-blue-600" : "text-gray-400"}`} />
                  <span className="flex-1 truncate text-left">{tenant.name}</span>
                  {isActive && <Check className="h-4 w-4 text-blue-600 shrink-0" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
