import { z } from "zod";

export const devisLineSchema = z.object({
  designation: z.string().min(1, "La designation est obligatoire").max(255),
  quantite: z.number().int().min(1, "Quantite minimum 1"),
  prix_unitaire_ht: z.number().min(0, "Le prix ne peut pas etre negatif"),
  taux_tva: z.number().min(0).max(100),
});

export const devisCreateSchema = z.object({
  case_id: z.number().int().positive(),
  part_secu: z.number().min(0),
  part_mutuelle: z.number().min(0),
  lignes: z.array(devisLineSchema).min(1, "Au moins une ligne est requise"),
});

export type DevisLineFormData = z.infer<typeof devisLineSchema>;
export type DevisCreateFormData = z.infer<typeof devisCreateSchema>;
