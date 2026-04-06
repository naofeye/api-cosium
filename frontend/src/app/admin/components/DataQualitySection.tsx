"use client";

import useSWR from "swr";
import { CompletionGauge } from "@/components/pec/CompletionGauge";
import { ErrorState } from "@/components/ui/ErrorState";
import { Database, FileText, CreditCard, FolderOpen, Stethoscope } from "lucide-react";

interface DataQualityEntity {
  total: number;
  linked: number;
  orphan: number;
  link_rate: number;
}

interface DataQualityData {
  invoices: DataQualityEntity;
  payments: DataQualityEntity;
  documents: DataQualityEntity;
  prescriptions: DataQualityEntity;
}

function getGaugeColor(rate: number): string {
  if (rate >= 90) return "text-emerald-700";
  if (rate >= 70) return "text-amber-700";
  return "text-red-700";
}

interface GaugeCardProps {
  label: string;
  entity: DataQualityEntity;
  icon: React.ComponentType<{ className?: string; "aria-hidden"?: boolean }>;
}

function GaugeCard({ label, entity, icon: Icon }: GaugeCardProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-5 shadow-sm">
      <div className="flex items-center gap-2 mb-3">
        <Icon className="h-4 w-4 text-text-secondary" aria-hidden={true} />
        <h4 className="text-sm font-semibold text-text-primary">{label}</h4>
      </div>
      <CompletionGauge score={entity.link_rate} />
      <div className="mt-3 grid grid-cols-3 gap-2 text-xs text-text-secondary">
        <div>
          <span className="block font-semibold text-text-primary tabular-nums">{entity.total}</span>
          Total
        </div>
        <div>
          <span className="block font-semibold text-emerald-700 tabular-nums">{entity.linked}</span>
          Lies
        </div>
        <div>
          <span className={`block font-semibold tabular-nums ${entity.orphan > 0 ? "text-red-600" : "text-text-secondary"}`}>
            {entity.orphan}
          </span>
          Orphelins
        </div>
      </div>
    </div>
  );
}

export function DataQualitySection() {
  const { data, error, mutate } = useSWR<DataQualityData>("/admin/data-quality", {
    refreshInterval: 60000,
  });

  if (error) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Database className="h-5 w-5 text-text-secondary" aria-hidden="true" />
          Qualite des donnees
        </h3>
        <ErrorState message="Impossible de charger la qualite des donnees" onRetry={() => mutate()} />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
          <Database className="h-5 w-5 text-text-secondary" aria-hidden="true" />
          Qualite des donnees
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-xl border border-border bg-bg-card p-5 shadow-sm animate-pulse">
              <div className="h-4 w-24 bg-gray-200 rounded mb-3" />
              <div className="h-3 w-full bg-gray-200 rounded mb-3" />
              <div className="h-3 w-16 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mb-6">
      <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
        <Database className="h-5 w-5 text-text-secondary" aria-hidden="true" />
        Qualite des donnees
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GaugeCard label="Factures" entity={data.invoices} icon={FileText} />
        <GaugeCard label="Paiements" entity={data.payments} icon={CreditCard} />
        <GaugeCard label="Documents" entity={data.documents} icon={FolderOpen} />
        <GaugeCard label="Ordonnances" entity={data.prescriptions} icon={Stethoscope} />
      </div>
    </div>
  );
}
