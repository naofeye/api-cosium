"use client";

import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import type { BatchItem } from "@/lib/types";
import { CompletionBar } from "./CompletionBar";

interface BatchItemsTableProps {
  items: BatchItem[];
}

export function BatchItemsTable({ items }: BatchItemsTableProps) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-white shadow-sm mb-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-border bg-gray-50 text-left">
            <th className="px-4 py-3 font-medium text-text-secondary">Client</th>
            <th className="px-4 py-3 font-medium text-text-secondary">Statut</th>
            <th className="px-4 py-3 font-medium text-text-secondary">Completude</th>
            <th className="px-4 py-3 font-medium text-text-secondary">Erreurs</th>
            <th className="px-4 py-3 font-medium text-text-secondary">Alertes</th>
            <th className="px-4 py-3 font-medium text-text-secondary">Action</th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-8 text-center text-text-secondary">
                Aucun element dans cette categorie.
              </td>
            </tr>
          ) : (
            items.map((item) => (
              <tr
                key={item.id}
                className="border-b border-border last:border-0 hover:bg-gray-50"
              >
                <td className="px-4 py-3">
                  <Link
                    href={`/clients/${item.customer_id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {item.customer_name}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={item.status} />
                </td>
                <td className="px-4 py-3">
                  <CompletionBar score={item.completude_score} />
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {item.errors_count > 0 ? (
                    <span className="text-red-600 font-medium">{item.errors_count}</span>
                  ) : (
                    <span className="text-text-secondary">0</span>
                  )}
                </td>
                <td className="px-4 py-3 tabular-nums">
                  {item.warnings_count > 0 ? (
                    <span className="text-amber-600 font-medium">{item.warnings_count}</span>
                  ) : (
                    <span className="text-text-secondary">0</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {item.pec_preparation_id ? (
                    <Link
                      href="/pec-dashboard"
                      className="inline-flex items-center gap-1 text-sm text-blue-600 hover:underline"
                    >
                      Voir PEC
                    </Link>
                  ) : (
                    <span className="text-text-secondary text-xs">-</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
