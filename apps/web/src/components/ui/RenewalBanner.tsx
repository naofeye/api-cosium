"use client";

import { AlertCircle, Clock, Sparkles } from "lucide-react";
import Link from "next/link";

interface RenewalBannerProps {
  /**
   * Date ISO de la derniere equipement achete par le client.
   * Si null/absent, pas de banniere.
   */
  lastEquipmentDate?: string | null;
  /** URL cible du bouton "Planifier RDV" (optionnel). */
  rdvHref?: string;
  /** Callback personnalise ; si absent, le bouton pointe vers rdvHref. */
  onSchedule?: () => void;
}

/**
 * Banniere alerte renouvellement affichee si le dernier equipement date de
 * plus de 2 ans. Encourage la planification d'un bilan de vue.
 */
export function RenewalBanner({ lastEquipmentDate, rdvHref, onSchedule }: RenewalBannerProps) {
  if (!lastEquipmentDate) return null;

  const last = new Date(lastEquipmentDate);
  if (Number.isNaN(last.getTime())) return null;
  const ageMonths = (Date.now() - last.getTime()) / (1000 * 60 * 60 * 24 * 30);

  if (ageMonths < 24) return null;

  const ageYears = Math.floor(ageMonths / 12);
  const urgency = ageMonths >= 36 ? "urgent" : "recommande";

  const palette =
    urgency === "urgent"
      ? {
          bg: "bg-red-50 border-red-200",
          icon: "text-red-600 bg-red-100",
          text: "text-red-900",
          btn: "bg-red-600 text-white hover:bg-red-700",
        }
      : {
          bg: "bg-amber-50 border-amber-200",
          icon: "text-amber-600 bg-amber-100",
          text: "text-amber-900",
          btn: "bg-amber-600 text-white hover:bg-amber-700",
        };

  const title = urgency === "urgent"
    ? `Renouvellement urgent (${ageYears} ans)`
    : `Renouvellement conseille (${ageYears} ans)`;
  const description =
    urgency === "urgent"
      ? "L'equipement a plus de 3 ans. Un bilan de vue est fortement recommande."
      : "L'equipement a plus de 2 ans. C'est le moment ideal pour un bilan de vue.";
  const Icon = urgency === "urgent" ? AlertCircle : Clock;

  return (
    <div className={`flex items-start gap-3 rounded-xl border p-4 mb-4 ${palette.bg}`} role="status">
      <div className={`flex h-10 w-10 flex-none items-center justify-center rounded-lg ${palette.icon}`}>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="flex-1">
        <p className={`text-sm font-semibold ${palette.text}`}>{title}</p>
        <p className={`mt-0.5 text-xs ${palette.text} opacity-90`}>{description}</p>
      </div>
      {onSchedule ? (
        <button
          type="button"
          onClick={onSchedule}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium shadow-sm ${palette.btn}`}
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          Planifier
        </button>
      ) : rdvHref ? (
        <Link
          href={rdvHref}
          className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-medium shadow-sm ${palette.btn}`}
        >
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          Planifier
        </Link>
      ) : null}
    </div>
  );
}
