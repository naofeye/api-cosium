"use client";

import { Button } from "@/components/ui/Button";

import type { Delivery } from "./types";

interface Props {
  delivery: Delivery;
  onClose: () => void;
}

export function DeliveryDetailModal({ delivery, onClose }: Props) {
  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Detail delivery webhook"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <h2 className="text-lg font-semibold mb-4">
            Delivery #{delivery.id} - {delivery.event_type}
          </h2>
          <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
            <div>
              <span className="text-gray-500">Statut</span>
              <p className="font-medium">{delivery.status}</p>
            </div>
            <div>
              <span className="text-gray-500">Tentatives</span>
              <p className="font-medium tabular-nums">{delivery.attempts}</p>
            </div>
            <div>
              <span className="text-gray-500">Code HTTP</span>
              <p className="font-medium tabular-nums">{delivery.last_status_code ?? "—"}</p>
            </div>
            <div>
              <span className="text-gray-500">Duree</span>
              <p className="font-medium tabular-nums">{delivery.duration_ms ?? "—"} ms</p>
            </div>
            <div className="col-span-2">
              <span className="text-gray-500">Event ID (idempotence)</span>
              <p className="font-mono text-xs break-all">{delivery.event_id}</p>
            </div>
          </div>
          {delivery.last_error && (
            <div className="mb-4">
              <span className="text-xs text-gray-500 uppercase font-semibold">
                Derniere erreur
              </span>
              <pre className="mt-1 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-900 overflow-x-auto whitespace-pre-wrap">
                {delivery.last_error}
              </pre>
            </div>
          )}
          {delivery.payload && (
            <div className="mb-4">
              <span className="text-xs text-gray-500 uppercase font-semibold">
                Payload envoye
              </span>
              <pre className="mt-1 p-3 bg-gray-50 border border-gray-200 rounded text-xs overflow-x-auto">
                {JSON.stringify(delivery.payload, null, 2)}
              </pre>
            </div>
          )}
          <div className="flex justify-end">
            <Button variant="outline" onClick={onClose}>
              Fermer
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
