import { z } from "zod";

/**
 * Payload de création d'une facture — génération depuis un devis signé.
 * Miroir de `FactureCreate` (apps/api/app/domain/schemas/factures.py).
 */
export const factureCreateSchema = z.object({
  devis_id: z
    .number()
    .int("L'identifiant du devis doit être un entier")
    .positive("L'identifiant du devis doit être positif"),
});

export type FactureCreateFormData = z.infer<typeof factureCreateSchema>;
