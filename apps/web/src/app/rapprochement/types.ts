export interface BankTx {
  id: number;
  date: string;
  libelle: string;
  montant: number;
  reference: string | null;
  reconciled: boolean;
  reconciled_payment_id: number | null;
}

export interface TxList {
  items: BankTx[];
  total: number;
}

export interface PaymentItem {
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
