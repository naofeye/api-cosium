"use client";

import useSWR from "swr";

interface MetricsData {
  totals: {
    clients: number;
    dossiers: number;
    factures: number;
    paiements: number;
  };
  activity: {
    actions_last_hour: number;
    active_users_last_hour: number;
  };
}

interface DataQualityData {
  documents: { total: number };
  invoices: { total: number };
}

function formatNumber(n: number): string {
  return n.toLocaleString("fr-FR");
}

export function StatsFooter() {
  const { data: metrics } = useSWR<MetricsData>("/admin/metrics", {
    refreshInterval: 120000,
    revalidateOnFocus: false,
    errorRetryCount: 1,
  });

  const { data: quality } = useSWR<DataQualityData>("/admin/data-quality", {
    refreshInterval: 120000,
    revalidateOnFocus: false,
    errorRetryCount: 1,
  });

  if (!metrics) return null;

  const clients = metrics.totals.clients;
  const factures = metrics.totals.factures;
  const documents = quality?.documents?.total ?? 0;
  const actionsLastHour = metrics.activity.actions_last_hour;

  return (
    <footer
      className="fixed bottom-0 left-0 right-0 z-20 hidden lg:flex items-center justify-center gap-6 h-8 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-t border-gray-100 dark:border-gray-800 text-xs text-gray-400 dark:text-gray-500 ml-64"
      aria-label="Statistiques globales"
    >
      <span>{formatNumber(clients)} clients</span>
      <span className="text-gray-300 dark:text-gray-600">|</span>
      <span>{formatNumber(factures)} factures</span>
      <span className="text-gray-300 dark:text-gray-600">|</span>
      <span>{formatNumber(documents)} documents</span>
      <span className="text-gray-300 dark:text-gray-600">|</span>
      <span>
        {actionsLastHour > 0
          ? `${actionsLastHour} action${actionsLastHour > 1 ? "s" : ""} cette heure`
          : "Aucune activite recente"}
      </span>
      <span className="text-gray-300 dark:text-gray-600">|</span>
      <span>v0.1.0</span>
    </footer>
  );
}
