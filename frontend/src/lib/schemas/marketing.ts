import { z } from "zod";

export const segmentCreateSchema = z.object({
  name: z.string().min(1, "Le nom du segment est obligatoire").max(255),
  description: z.string().max(500).optional().or(z.literal("")),
});

export const campaignCreateSchema = z.object({
  name: z.string().min(1, "Le nom de la campagne est obligatoire").max(255),
  segment_id: z.coerce.number().int().positive("Selectionnez un segment"),
  channel: z.enum(["email", "sms"]),
  subject: z.string().max(500).optional().or(z.literal("")),
  template: z.string().min(1, "Le contenu du message est obligatoire"),
});

export type SegmentCreateFormData = z.infer<typeof segmentCreateSchema>;
export type CampaignCreateFormData = z.infer<typeof campaignCreateSchema>;
