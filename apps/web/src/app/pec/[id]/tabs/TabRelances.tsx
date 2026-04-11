"use client";

import { DateDisplay } from "@/components/ui/DateDisplay";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { Phone, Mail, FileText } from "lucide-react";

export interface RelanceItem {
  id: number;
  type: string;
  date_envoi: string;
  contenu: string | null;
  created_by: number;
}

export interface TabRelancesProps {
  relances: RelanceItem[];
  relanceType: string;
  onRelanceTypeChange: (value: string) => void;
  relanceContenu: string;
  onRelanceContenuChange: (value: string) => void;
  submittingRelance: boolean;
  onAddRelance: () => void;
}

const RELANCE_ICONS: Record<string, typeof Phone> = {
  email: Mail,
  telephone: Phone,
  courrier: FileText,
};

export function TabRelances({
  relances,
  relanceType,
  onRelanceTypeChange,
  relanceContenu,
  onRelanceContenuChange,
  submittingRelance,
  onAddRelance,
}: TabRelancesProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
        <h4 className="text-sm font-semibold text-text-primary mb-3">Nouvelle relance</h4>
        <div className="flex gap-3">
          <select
            value={relanceType}
            onChange={(e) => onRelanceTypeChange(e.target.value)}
            className="rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          >
            <option value="email">Email</option>
            <option value="telephone">Telephone</option>
            <option value="courrier">Courrier</option>
          </select>
          <input
            type="text"
            value={relanceContenu}
            onChange={(e) => onRelanceContenuChange(e.target.value)}
            placeholder="Contenu de la relance..."
            className="flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          />
          <Button onClick={onAddRelance} disabled={submittingRelance}>
            {submittingRelance ? "Envoi..." : "Envoyer"}
          </Button>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-bg-card shadow-sm">
        {relances.length === 0 ? (
          <div className="p-6">
            <EmptyState title="Aucune relance" description="Les relances envoyees apparaitront ici." />
          </div>
        ) : (
          <div className="divide-y divide-border">
            {relances.map((r) => {
              const Icon = RELANCE_ICONS[r.type] || Mail;
              return (
                <div key={r.id} className="flex items-start gap-3 px-5 py-3">
                  <Icon className="h-4 w-4 text-text-secondary mt-0.5 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium capitalize">{r.type}</span>
                      <span className="text-xs text-text-secondary">
                        <DateDisplay date={r.date_envoi} />
                      </span>
                    </div>
                    {r.contenu && <p className="text-sm text-text-secondary mt-0.5">{r.contenu}</p>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
