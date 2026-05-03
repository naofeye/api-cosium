import { redirect } from "next/navigation";

/**
 * Redirection 308 vers /admin/api-publique (la page Coming Soon T3 2026 est
 * devenue reelle le 2026-05-03 — API publique read-only v1).
 */
export default function ApiPubliqueRedirect(): never {
  redirect("/admin/api-publique");
}
