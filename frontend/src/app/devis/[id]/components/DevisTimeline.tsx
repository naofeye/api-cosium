import { Check, XCircle } from "lucide-react";
import { formatDate } from "@/lib/format";

export interface DevisLigne {
  id: number;
  designation: string;
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
  montant_ht: number;
  montant_ttc: number;
}

export interface DevisDetail {
  id: number;
  case_id: number;
  numero: string;
  status: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  part_secu: number;
  part_mutuelle: number;
  reste_a_charge: number;
  created_at: string;
  updated_at: string | null;
  sent_at?: string | null;
  signed_at?: string | null;
  invoiced_at?: string | null;
  facture_id?: number | null;
  lignes: DevisLigne[];
  customer_name: string | null;
}

interface TimelineStep {
  key: string;
  label: string;
  dateField: keyof DevisDetail;
}

const TIMELINE_STEPS: TimelineStep[] = [
  { key: "brouillon", label: "Brouillon", dateField: "created_at" },
  { key: "envoye", label: "Envoye", dateField: "sent_at" },
  { key: "signe", label: "Signe", dateField: "signed_at" },
  { key: "facture", label: "Facture", dateField: "invoiced_at" },
];

const STATUS_ORDER: Record<string, number> = {
  brouillon: 0,
  envoye: 1,
  signe: 2,
  facture: 3,
  annule: -1,
  refuse: -1,
};

export function DevisTimeline({ devis }: { devis: DevisDetail }) {
  const currentIdx = STATUS_ORDER[devis.status] ?? -1;
  const isTerminal = devis.status === "annule" || devis.status === "refuse";

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
        Progression du devis
      </h3>
      {isTerminal ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100">
            <XCircle className="h-5 w-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-red-700 capitalize">{devis.status.replace(/_/g, " ")}</p>
            {devis.updated_at && (
              <p className="text-xs text-text-secondary">{formatDate(devis.updated_at)}</p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-0">
          {TIMELINE_STEPS.map((step, idx) => {
            const stepIdx = idx;
            const isCompleted = stepIdx < currentIdx;
            const isCurrent = stepIdx === currentIdx;
            const dateValue = devis[step.dateField];
            const dateStr = typeof dateValue === "string" ? dateValue : null;

            return (
              <div key={step.key} className="flex items-center flex-1 last:flex-none">
                <div className="flex flex-col items-center min-w-0">
                  <div
                    className={`flex items-center justify-center w-9 h-9 rounded-full border-2 transition-colors ${
                      isCompleted
                        ? "bg-emerald-600 border-emerald-600"
                        : isCurrent
                          ? "bg-blue-600 border-blue-600"
                          : "bg-white border-gray-300"
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4 text-white" />
                    ) : isCurrent ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-white" />
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                    )}
                  </div>
                  <p
                    className={`mt-2 text-xs font-medium ${
                      isCompleted ? "text-emerald-700" : isCurrent ? "text-blue-700" : "text-text-secondary"
                    }`}
                  >
                    {step.label}
                  </p>
                  {dateStr && (
                    <p className="text-[10px] text-text-secondary mt-0.5">{formatDate(dateStr)}</p>
                  )}
                </div>
                {idx < TIMELINE_STEPS.length - 1 && (
                  <div className="flex-1 mx-2 mt-[-1.5rem]">
                    <div
                      className={`h-0.5 w-full ${
                        stepIdx < currentIdx ? "bg-emerald-500" : "bg-gray-200"
                      }`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
