"use client";

import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { DraggableTransaction } from "./DraggableTransaction";
import { DroppablePayment } from "./DroppablePayment";
import { AlertCircle, Link2, GripVertical } from "lucide-react";

interface BankTx {
  id: number;
  date: string;
  libelle: string;
  montant: number;
  reference: string | null;
  reconciled: boolean;
  reconciled_payment_id: number | null;
}

interface PaymentItem {
  id: number;
  case_id: number;
  payer_type: string;
  mode_paiement: string | null;
  reference_externe: string | null;
  date_paiement: string | null;
  amount_due: number;
  amount_paid: number;
  status: string;
}

interface ManualReconciliationProps {
  unmatchedTx: BankTx[];
  payments: PaymentItem[];
  onMatch: (transactionId: number, paymentId: number) => Promise<void>;
}

export function ManualReconciliation({ unmatchedTx, payments, onMatch }: ManualReconciliationProps) {
  if (unmatchedTx.length === 0 && payments.length === 0) return null;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <GripVertical className="h-4 w-4 text-gray-400" aria-hidden="true" />
        <h2 className="text-lg font-semibold text-gray-800">Rapprochement manuel</h2>
      </div>
      <p className="text-sm text-gray-500 mb-4">Glissez une transaction sur un paiement pour les rapprocher.</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left column: Unmatched transactions */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-500" />
            Transactions non rapprochees ({unmatchedTx.length})
          </h3>
          {unmatchedTx.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-6 text-center text-sm text-gray-400">
              Toutes les transactions sont rapprochees
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {unmatchedTx.map((tx) => (
                <DraggableTransaction key={tx.id} id={tx.id}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <GripVertical
                        className="h-4 w-4 text-gray-300 flex-shrink-0"
                        aria-label="Glisser pour rapprocher"
                      />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{tx.libelle}</p>
                        <p className="text-xs text-gray-500">
                          <DateDisplay date={tx.date} />
                          {tx.reference && <span className="ml-2 font-mono">{tx.reference}</span>}
                        </p>
                      </div>
                    </div>
                    <MoneyDisplay amount={tx.montant} colored />
                  </div>
                </DraggableTransaction>
              ))}
            </div>
          )}
        </div>

        {/* Right column: Unreconciled payments */}
        <div>
          <h3 className="text-sm font-medium text-gray-700 mb-3 flex items-center gap-2">
            <Link2 className="h-4 w-4 text-blue-500" />
            Paiements a rapprocher ({payments.length})
          </h3>
          {payments.length === 0 ? (
            <div className="border border-dashed border-border rounded-lg p-6 text-center text-sm text-gray-400">
              Aucun paiement en attente de rapprochement
            </div>
          ) : (
            <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
              {payments.map((p) => (
                <DroppablePayment key={p.id} id={p.id} onMatch={onMatch}>
                  <div className="flex items-center justify-between">
                    <div className="min-w-0">
                      <p className="text-sm font-medium">
                        Paiement #{p.id}
                        <span className="ml-2 text-xs text-gray-500">{p.payer_type}</span>
                      </p>
                      <p className="text-xs text-gray-500">
                        {p.date_paiement && <DateDisplay date={p.date_paiement} />}
                        {p.mode_paiement && <span className="ml-2">{p.mode_paiement}</span>}
                        {p.reference_externe && <span className="ml-2 font-mono">{p.reference_externe}</span>}
                      </p>
                    </div>
                    <MoneyDisplay amount={p.amount_paid} colored />
                  </div>
                </DroppablePayment>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
