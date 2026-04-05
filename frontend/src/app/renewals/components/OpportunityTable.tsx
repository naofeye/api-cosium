"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { TrendingUp, Send, Mail, Phone, MessageSquare } from "lucide-react";

export interface RenewalOpportunity {
  customer_id: number;
  customer_name: string;
  phone: string | null;
  email: string | null;
  last_purchase_date: string | null;
  months_since_purchase: number;
  equipment_type: string | null;
  last_invoice_amount: number;
  has_active_mutuelle: boolean;
  score: number;
  suggested_action: string;
  reason: string;
}

interface OpportunityTableProps {
  opportunities: RenewalOpportunity[];
  selected: Set<number>;
  onToggleSelect: (id: number) => void;
  onSelectAll: () => void;
  onSelectHighScore: () => void;
  onGoToCampaign: () => void;
}

const EQUIPMENT_LABELS: Record<string, string> = {
  monture: "Monture",
  verre: "Verres",
  lentille: "Lentilles",
  solaire: "Solaires",
  autre: "Autre",
};

const ACTION_ICONS: Record<string, typeof Mail> = {
  email: Mail,
  sms: MessageSquare,
  telephone: Phone,
  courrier: Send,
};

function ScoreBadge({ score }: { score: number }) {
  const colorClass =
    score >= 70
      ? "bg-emerald-100 text-emerald-700"
      : score >= 40
        ? "bg-amber-100 text-amber-700"
        : "bg-sky-100 text-sky-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium tabular-nums ${colorClass}`}
    >
      {score}
    </span>
  );
}

export function OpportunityTable({
  opportunities,
  selected,
  onToggleSelect,
  onSelectAll,
  onSelectHighScore,
  onGoToCampaign,
}: OpportunityTableProps) {
  if (opportunities.length === 0) {
    return (
      <EmptyState
        title="Aucune opportunite de renouvellement"
        description="Aucun client n'a un equipement datant de plus de 24 mois. Revenez plus tard ou ajustez les criteres."
      />
    );
  }

  return (
    <>
      <div className="flex items-center gap-3 mb-4">
        <Button variant="outline" size="sm" onClick={onSelectAll}>
          {selected.size === opportunities.length ? "Tout deselectionner" : "Tout selectionner"}
        </Button>
        <Button variant="outline" size="sm" onClick={onSelectHighScore}>
          <TrendingUp className="mr-1 h-3 w-3" /> Selectionner fort potentiel
        </Button>
        {selected.size > 0 && (
          <Button size="sm" onClick={onGoToCampaign}>
            <Send className="mr-1 h-3 w-3" /> Campagne ({selected.size})
          </Button>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th scope="col" className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  checked={selected.size === opportunities.length}
                  onChange={onSelectAll}
                  aria-label="Tout selectionner"
                />
              </th>
              <th scope="col" className="px-4 py-3">Client</th>
              <th scope="col" className="px-4 py-3">Equipement</th>
              <th scope="col" className="px-4 py-3">Dernier achat</th>
              <th scope="col" className="px-4 py-3">Mois</th>
              <th scope="col" className="px-4 py-3">Montant</th>
              <th scope="col" className="px-4 py-3">Mutuelle</th>
              <th scope="col" className="px-4 py-3">Score</th>
              <th scope="col" className="px-4 py-3">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {opportunities.map((o) => {
              const ActionIcon = ACTION_ICONS[o.suggested_action] || Send;
              return (
                <tr key={o.customer_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <input
                      type="checkbox"
                      checked={selected.has(o.customer_id)}
                      onChange={() => onToggleSelect(o.customer_id)}
                      aria-label={`Selectionner ${o.customer_name}`}
                    />
                  </td>
                  <td className="px-4 py-3 font-medium">{o.customer_name}</td>
                  <td className="px-4 py-3">
                    {o.equipment_type ? EQUIPMENT_LABELS[o.equipment_type] || o.equipment_type : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {o.last_purchase_date ? <DateDisplay date={o.last_purchase_date} /> : "—"}
                  </td>
                  <td className="px-4 py-3 tabular-nums">{o.months_since_purchase}</td>
                  <td className="px-4 py-3 tabular-nums">
                    <MoneyDisplay amount={o.last_invoice_amount} />
                  </td>
                  <td className="px-4 py-3">
                    {o.has_active_mutuelle ? (
                      <span className="text-xs font-medium text-success">Oui</span>
                    ) : (
                      <span className="text-xs text-text-secondary">Non</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ScoreBadge score={o.score} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-text-secondary" title={o.suggested_action}>
                      <ActionIcon className="h-4 w-4" />
                      <span className="text-xs capitalize">{o.suggested_action}</span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
