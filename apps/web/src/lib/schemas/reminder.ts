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

export type ReminderPlanFormData = z.infer<typeof reminderPlanSchema>;
export type ReminderTemplateFormData = z.infer<typeof reminderTemplateSchema>;
