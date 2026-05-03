"use client";

import { Trash2 } from "lucide-react";

import { Button } from "@/components/ui/Button";
import { type Column } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";

import type { Delivery, Subscription } from "./types";

const STATUS_STYLES: Record<string, string> = {
  success: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  pending: "bg-blue-50 text-blue-700 ring-blue-200",
  retrying: "bg-amber-50 text-amber-700 ring-amber-200",
  failed: "bg-red-50 text-red-700 ring-red-200",
};

export function DeliveryStatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? "bg-gray-50 text-gray-700 ring-gray-200";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      {status}
    </span>
  );
}

interface SubColumnsHandlers {
  onTestPing: (sub: Subscription) => void;
  onToggle: (sub: Subscription) => void;
  onDelete: (sub: Subscription) => void;
  pingingId: number | null;
}

export function buildSubscriptionColumns({
  onTestPing,
  onToggle,
  onDelete,
  pingingId,
}: SubColumnsHandlers): Column<Subscription>[] {
  return [
    {
      key: "name",
      header: "Nom",
      render: (s) => (
        <div className="flex flex-col">
          <span className="font-medium text-gray-900">{s.name}</span>
          {s.description && <span className="text-xs text-gray-500">{s.description}</span>}
        </div>
      ),
    },
    {
      key: "url",
      header: "URL",
      render: (s) => (
        <span className="font-mono text-xs text-gray-600 break-all">{s.url}</span>
      ),
    },
    {
      key: "event_types",
      header: "Evenements",
      render: (s) => (
        <div className="flex flex-wrap gap-1">
          {s.event_types.map((e) => (
            <span
              key={e}
              className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
            >
              {e}
            </span>
          ))}
        </div>
      ),
    },
    {
      key: "is_active",
      header: "Statut",
      render: (s) => (
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${
            s.is_active
              ? "bg-emerald-50 text-emerald-700 ring-emerald-200"
              : "bg-gray-50 text-gray-500 ring-gray-200"
          }`}
        >
          {s.is_active ? "Actif" : "Inactif"}
        </span>
      ),
    },
    {
      key: "secret_masked",
      header: "Secret",
      render: (s) => <span className="font-mono text-xs">{s.secret_masked}</span>,
    },
    {
      key: "actions",
      header: "Actions",
      render: (s) => (
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onTestPing(s)}
            disabled={!s.is_active || pingingId === s.id}
            aria-label={`Tester ${s.name}`}
          >
            {pingingId === s.id ? "..." : "Test"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => onToggle(s)}>
            {s.is_active ? "Desactiver" : "Activer"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onDelete(s)}
            aria-label={`Supprimer ${s.name}`}
          >
            <Trash2 size={14} />
          </Button>
        </div>
      ),
    },
  ];
}

interface DeliveryColumnsHandlers {
  onShowDetail: (delivery: Delivery) => void;
  onReplay: (delivery: Delivery) => void;
}

export function buildDeliveryColumns({
  onShowDetail,
  onReplay,
}: DeliveryColumnsHandlers): Column<Delivery>[] {
  return [
    {
      key: "created_at",
      header: "Date",
      render: (d) => <DateDisplay date={d.created_at} />,
    },
    {
      key: "event_type",
      header: "Evenement",
      render: (d) => <span className="font-mono text-xs">{d.event_type}</span>,
    },
    {
      key: "status",
      header: "Statut",
      render: (d) => <DeliveryStatusBadge status={d.status} />,
    },
    {
      key: "attempts",
      header: "Tentatives",
      render: (d) => <span className="font-mono">{d.attempts}</span>,
    },
    {
      key: "last_status_code",
      header: "Code HTTP",
      render: (d) =>
        d.last_status_code !== null ? (
          <span className="font-mono">{d.last_status_code}</span>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
    {
      key: "duration_ms",
      header: "Duree",
      render: (d) =>
        d.duration_ms !== null ? (
          <span className="font-mono text-xs">{d.duration_ms} ms</span>
        ) : (
          <span className="text-gray-400">—</span>
        ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (d) => (
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onShowDetail(d)}>
            Detail
          </Button>
          {d.status === "failed" && (
            <Button variant="outline" size="sm" onClick={() => onReplay(d)}>
              Rejouer
            </Button>
          )}
        </div>
      ),
    },
  ];
}
