"use client";

import { useCallback, useEffect, useState } from "react";
import {
  getTenantId,
  getTenantName,
  getAvailableTenants,
  switchTenant as authSwitchTenant,
  type AvailableTenant,
} from "./auth";

interface TenantContext {
  tenantId: number | undefined;
  tenantName: string | undefined;
  availableTenants: AvailableTenant[];
  isMultiTenant: boolean;
  switchTenant: (tenantId: number) => Promise<void>;
}

export function useTenant(): TenantContext {
  const [tenantId, setTenantId] = useState<number | undefined>(undefined);
  const [tenantName, setTenantName] = useState<string | undefined>(undefined);
  const [availableTenants, setAvailableTenants] = useState<AvailableTenant[]>([]);

  useEffect(() => {
    setTenantId(getTenantId());
    setTenantName(getTenantName());
    setAvailableTenants(getAvailableTenants());
  }, []);

  const switchTenant = useCallback(async (newTenantId: number) => {
    const result = await authSwitchTenant(newTenantId);
    setTenantId(result.tenant_id);
    setTenantName(result.tenant_name);
    setAvailableTenants(result.available_tenants);
    // Recharger la page pour rafraichir toutes les donnees du nouveau tenant
    window.location.reload();
  }, []);

  return {
    tenantId,
    tenantName,
    availableTenants,
    isMultiTenant: availableTenants.length > 1,
    switchTenant,
  };
}
