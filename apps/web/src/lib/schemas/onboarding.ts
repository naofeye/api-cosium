import { z } from "zod";

export const signupSchema = z.object({
  company_name: z.string().min(2, "Nom de l'entreprise requis (2 caracteres min.)").max(255),
  owner_email: z.string().email("Adresse email invalide"),
  owner_password: z
    .string()
    .min(8, "8 caracteres minimum")
    .regex(/[A-Z]/, "Au moins une majuscule")
    .regex(/\d/, "Au moins un chiffre"),
  owner_first_name: z.string().min(1, "Le prenom est obligatoire").max(100),
  owner_last_name: z.string().min(1, "Le nom est obligatoire").max(100),
  phone: z.string().max(50).optional().or(z.literal("")),
});

export const cosiumConnectSchema = z.object({
  cosium_tenant: z.string().min(1, "Le code site Cosium est obligatoire").max(100),
  cosium_login: z.string().min(1, "Le login est obligatoire").max(255),
  cosium_password: z.string().min(1, "Le mot de passe est obligatoire").max(255),
});

export type SignupFormData = z.infer<typeof signupSchema>;
export type CosiumConnectFormData = z.infer<typeof cosiumConnectSchema>;
