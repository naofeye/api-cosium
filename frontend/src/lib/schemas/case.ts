import { z } from "zod";

export const caseCreateSchema = z.object({
  first_name: z.string().min(1, "Le prenom est obligatoire").max(120),
  last_name: z.string().min(1, "Le nom est obligatoire").max(120),
  phone: z.string().max(50).optional().or(z.literal("")),
  email: z.string().email("Adresse email invalide").optional().or(z.literal("")),
  source: z.string().min(1),
});

export type CaseCreateFormData = z.infer<typeof caseCreateSchema>;
