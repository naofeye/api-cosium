import { z } from "zod";

export const reminderPlanSchema = z.object({
  name: z.string().min(1, "Le nom du plan est obligatoire").max(255),
  payer_type: z.enum(["client", "mutuelle", "secu"]),
  interval_days: z.number().int().min(1, "Minimum 1 jour"),
  is_active: z.boolean(),
});

export const reminderTemplateSchema = z.object({
  name: z.string().min(1, "Le nom du template est obligatoire").max(255),
  channel: z.enum(["email", "sms", "courrier", "telephone"]),
  payer_type: z.enum(["client", "mutuelle", "secu"]),
  subject: z.string().max(500).optional().or(z.literal("")),
  body: z.string().min(1, "Le contenu est obligatoire"),
  is_default: z.boolean(),
});

/**
 * Payload de création d'une relance manuelle — envoi ciblé client ou payer.
 * Miroir de `ReminderCreate` (apps/api/app/domain/schemas/reminders.py).
 * Prévu pour l'UI d'envoi de relance depuis une fiche client / facture.
 */
export const reminderCreateSchema = z.object({
  target_type: z.enum(["client", "payer_organization"]),
  target_id: z
    .number()
    .int("L'identifiant cible doit être un entier")
    .positive("L'identifiant cible doit être positif"),
  facture_id: z.number().int().positive().nullable().optional(),
  pec_request_id: z.number().int().positive().nullable().optional(),
  channel: z.enum(["email", "sms", "courrier", "telephone"]).default("email"),
  content: z.string().max(5000).nullable().optional(),
});

export type ReminderPlanFormData = z.infer<typeof reminderPlanSchema>;
export type ReminderTemplateFormData = z.infer<typeof reminderTemplateSchema>;
export type ReminderCreateFormData = z.infer<typeof reminderCreateSchema>;
