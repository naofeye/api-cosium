import { redirect } from "next/navigation";

/**
 * Redirection 308 vers /admin/webhooks (la page Coming Soon est devenue
 * reelle le 2026-05-02). Conservée comme alias pour les liens externes
 * eventuels qui pointaient vers /webhooks.
 */
export default function WebhooksRedirect(): never {
  redirect("/admin/webhooks");
}
