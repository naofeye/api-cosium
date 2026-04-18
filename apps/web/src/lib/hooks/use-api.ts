/**
 * Re-export barrel pour compat : les hooks ont été déplacés par domaine
 * dans `hooks/clients.ts`, `hooks/cosium.ts`, `hooks/ai.ts`,
 * `hooks/marketing.ts`, `hooks/dashboard.ts`.
 *
 * Nouvelle convention : importer directement depuis le module domaine
 * (ex: `import { useClients } from "@/lib/hooks/clients"`) pour
 * faciliter le tree-shaking. Ce barrel reste en place pour les
 * imports existants et doit être préféré temps que pas migré.
 */
export * from "./clients";
export * from "./cosium";
export * from "./ai";
export * from "./marketing";
export * from "./dashboard";
