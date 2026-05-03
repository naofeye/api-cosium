"use client";

import Link from "next/link";
import { Activity, ChevronLeft, ExternalLink } from "lucide-react";

import { PageLayout } from "@/components/layout/PageLayout";
import { HealthDetail } from "../components/HealthDetail";

/**
 * Page dediee a la sante du systeme. HealthDetail (carte 4-col + queues)
 * full-width + liens externes vers les dashboards Grafana / Prometheus.
 */
export default function HealthPage() {
  return (
    <PageLayout
      title="Sante du systeme"
      description="Vue temps reel : services, pool DB, queues Celery, runtime versions."
      breadcrumb={[
        { label: "Administration", href: "/admin" },
        { label: "Sante systeme" },
      ]}
      actions={
        <Link
          href="/admin"
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
        >
          <ChevronLeft size={14} aria-hidden="true" />
          Retour
        </Link>
      }
    >
      <div className="space-y-6">
        <HealthDetail />

        <section className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h2 className="text-base font-semibold text-text-primary mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4" aria-hidden="true" />
            Dashboards externes
          </h2>
          <p className="text-sm text-text-secondary mb-4">
            Pour les metriques temporelles detaillees (latences, taux 5xx,
            evolution memoire, etc.), consultez les dashboards Grafana en
            production.
          </p>
          <ul className="space-y-2 text-sm">
            <li>
              <a
                href="https://grafana.ia.coging.com/d/optiflow-ops"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:underline"
              >
                <ExternalLink size={14} aria-hidden="true" />
                Grafana - Operations (req/s, p95, 5xx, PG, Redis)
              </a>
            </li>
            <li>
              <a
                href="https://grafana.ia.coging.com/d/optiflow-business"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:underline"
              >
                <ExternalLink size={14} aria-hidden="true" />
                Grafana - Business (sync Cosium, devis, CA, PEC, IA)
              </a>
            </li>
            <li>
              <a
                href="https://prometheus.ia.coging.com/alerts"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-blue-600 hover:underline"
              >
                <ExternalLink size={14} aria-hidden="true" />
                Prometheus - Alertes actives (api 5xx/latence, pool, queues)
              </a>
            </li>
          </ul>
          <p className="mt-4 text-xs text-text-secondary">
            Les liens redirigent vers les dashboards prod sous reverse-proxy
            authentifies. Acces admin requis.
          </p>
        </section>

        <section className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
          <p className="font-medium mb-1">Endpoints API utiles</p>
          <ul className="list-disc list-inside space-y-1 text-xs">
            <li><code>GET /api/v1/admin/health-detail</code> : snapshot complet</li>
            <li><code>GET /api/v1/admin/metrics</code> : metriques tenant</li>
            <li><code>GET /api/v1/metrics</code> : Prometheus scrape (Bearer)</li>
            <li><code>GET /health</code> : liveness check public (load balancer)</li>
          </ul>
        </section>
      </div>
    </PageLayout>
  );
}
