import { z } from "zod";

/**
 * Payload du rapprochement manuel transaction bancaire ↔ paiement.
 * Miroir de `ReconcileRequest` (apps/api/app/domain/schemas/banking.py).
 * Utilisé par le drag&drop de la page rapprochement.
 */
export const manualMatchSchema = z.object({
  transaction_id: z
    .number()
    .int("L'identifiant de transaction doit être un entier")
    .positive("L'identifiant de transaction doit être positif"),
  payment_id: z
    .number()
    .int("L'identifiant de paiement doit être un entier")
    .positive("L'identifiant de paiement doit être positif"),
});

export type ManualMatchPayload = z.infer<typeof manualMatchSchema>;
