import { z } from "zod";

export const paymentCreateSchema = z.object({
  case_id: z.number().int().positive("Selectionnez un dossier"),
  facture_id: z.number().int().positive().optional().or(z.literal(0)),
  payer_type: z.string().min(1, "Le type de payeur est obligatoire"),
  mode_paiement: z.string().optional().or(z.literal("")),
  amount_due: z.number().min(0, "Le montant ne peut pas etre negatif"),
  amount_paid: z.number().min(0.01, "Le montant paye doit etre superieur a 0"),
});

export type PaymentCreateFormData = z.infer<typeof paymentCreateSchema>;
