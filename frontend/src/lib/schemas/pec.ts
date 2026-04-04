import { z } from "zod";

export const pecCreateSchema = z.object({
  case_id: z.coerce.number().int().positive(),
  organization_id: z.coerce.number().int().positive("Selectionnez un organisme"),
  facture_id: z.coerce.number().int().positive().optional().or(z.literal(0)),
  montant_demande: z.coerce.number().min(0, "Le montant ne peut pas etre negatif"),
});

export type PecCreateFormData = z.infer<typeof pecCreateSchema>;
