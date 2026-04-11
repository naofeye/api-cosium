"use client";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { TrendingUp, Send, Mail, Phone, MessageSquare } from "lucide-react";

export interface PrescriptionSummary {
  prescription_date: string | null;
  age_months: number;
  od_summary: string;
  og_summary: string;
  prescriber_name: string | null;
}

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
  prescription: PrescriptionSummary | null;
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
              <th scope="col" className="px-4 py-3">Derniere ordonnance</th>
              <th scope="col" className="px-4 py-3">Age ordo.</th>
              <th scope="col" className="px-4 py-3">Correction (OD/OG)</th>
              <th scope="col" className="px-4 py-3">Contact</th>
              <th scope="col" className="px-4 py-3">Equipement</th>
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
                    {o.prescription?.prescription_date ? (
                      <DateDisplay date={o.prescription.prescription_date} />
                    ) : o.last_purchase_date ? (
                      <DateDisplay date={o.last_purchase_date} />
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="px-4 py-3 tabular-nums">
                    {o.prescription ? (
                      <span className={o.prescription.age_months >= 24 ? "text-red-600 font-medium" : "text-amber-600"}>
                        {o.prescription.age_months} mois
                      </span>
                    ) : (
                      <span>{o.months_since_purchase} mois</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {o.prescription && (o.prescription.od_summary || o.prescription.og_summary) ? (
                      <div className="text-xs space-y-0.5">
                        {o.prescription.od_summary && (
                          <div><span className="font-medium text-text-secondary">OD:</span> {o.prescription.od_summary}</div>
                        )}
                        {o.prescription.og_summary && (
                          <div><span className="font-medium text-text-secondary">OG:</span> {o.prescription.og_summary}</div>
                        )}
                      </div>
                    ) : (
                      <span className="text-text-secondary text-xs">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="text-xs space-y-0.5">
                      {o.phone && <div className="flex items-center gap-1"><Phone className="h-3 w-3 text-text-secondary" />{o.phone}</div>}
                      {o.email && <div className="flex items-center gap-1"><Mail className="h-3 w-3 text-text-secondary" />{o.email}</div>}
                      {!o.phone && !o.email && <span className="text-text-secondary">—</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {o.equipment_type ? EQUIPMENT_LABELS[o.equipment_type] || o.equipment_type : "—"}
                  </td>
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
                    <button
                      className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors"
                      title={`Contacter par ${o.suggested_action}`}
                      onClick={(e) => {
                        e.stopPropagation();
                        if (o.suggested_action === "email" && o.email) {
                          window.location.href = `mailto:${o.email}?subject=Renouvellement%20equipement%20optique`;
                        } else if ((o.suggested_action === "telephone" || o.suggested_action === "sms") && o.phone) {
                          window.location.href = `tel:${o.phone}`;
                        }
                      }}
                    >
                      <ActionIcon className="h-3.5 w-3.5" />
                      Contacter
                    </button>
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
