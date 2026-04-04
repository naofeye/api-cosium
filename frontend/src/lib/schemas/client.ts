import { z } from "zod";

export const clientCreateSchema = z.object({
  first_name: z.string().min(1, "Le prenom est obligatoire").max(120),
  last_name: z.string().min(1, "Le nom est obligatoire").max(120),
  phone: z.string().max(50).optional().or(z.literal("")),
  email: z.string().email("Adresse email invalide").optional().or(z.literal("")),
  address: z.string().max(255).optional().or(z.literal("")),
  city: z.string().max(120).optional().or(z.literal("")),
  postal_code: z.string().max(20).optional().or(z.literal("")),
  social_security_number: z.string().max(15).optional().or(z.literal("")),
  notes: z.string().max(1000).optional().or(z.literal("")),
});

export type ClientCreateFormData = z.infer<typeof clientCreateSchema>;
