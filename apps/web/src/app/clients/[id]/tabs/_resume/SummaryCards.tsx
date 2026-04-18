import {
  Activity,
  Calendar,
  Euro,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Shield,
  ShieldCheck,
  User,
} from "lucide-react";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { formatDate, formatMoney, formatPhone } from "@/lib/format";
import { InfoRow, TYPE_ICONS, formatAxis, formatDiopter } from "./shared";
import type {
  CalendarEvent,
  ClientMutuelleInfo,
  CorrectionActuelle,
  Interaction,
} from "./types";

export function PersonalInfoCard({
  firstName,
  lastName,
  phone,
  email,
  socialSecurityNumber,
  postalCode,
  city,
}: {
  firstName: string;
  lastName: string;
  phone: string | null;
  email: string | null;
  socialSecurityNumber: string | null;
  postalCode: string | null;
  city: string | null;
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Informations personnelles</h3>
      <div className="space-y-3 text-sm">
        <InfoRow icon={User} label="Nom" value={`${firstName} ${lastName}`} />
        <InfoRow
          icon={Phone}
          label="Telephone"
          value={phone ? formatPhone(phone) : "Non renseigne"}
          copyValue={phone || undefined}
        />
        <InfoRow
          icon={Mail}
          label="Email"
          value={email || "Non renseigne"}
          copyValue={email || undefined}
        />
        <InfoRow
          icon={Shield}
          label="N\u00B0 Secu"
          value={socialSecurityNumber || "Non renseigne"}
          copyValue={socialSecurityNumber || undefined}
        />
        <InfoRow
          icon={MapPin}
          label="Ville"
          value={city ? `${postalCode || ""} ${city}` : "Non renseignee"}
        />
      </div>
    </div>
  );
}

export function CosiumSummaryCard({
  totalCaCosium,
  lastVisitDate,
  nextRdv,
}: {
  totalCaCosium: number;
  lastVisitDate: string | null;
  nextRdv: CalendarEvent | null;
}) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Resume Cosium</h3>
      <div className="space-y-3 text-sm">
        <div className="flex items-center gap-3">
          <Euro className="h-4 w-4 text-text-secondary shrink-0" />
          <div className="flex justify-between flex-1">
            <span className="text-text-secondary">CA total Cosium</span>
            <span className="font-semibold text-base tabular-nums">
              {formatMoney(totalCaCosium)}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Calendar className="h-4 w-4 text-text-secondary shrink-0" />
          <div className="flex justify-between flex-1">
            <span className="text-text-secondary">Derniere visite</span>
            <span className="font-medium">
              {lastVisitDate ? formatDate(lastVisitDate) : "Inconnue"}
            </span>
          </div>
        </div>
        {nextRdv && (
          <div className="flex items-center gap-3">
            <Activity className="h-4 w-4 text-blue-500 shrink-0" />
            <div className="flex justify-between flex-1">
              <span className="text-text-secondary">Prochain RDV</span>
              <span className="font-medium text-blue-600">
                {nextRdv.start_date ? formatDate(nextRdv.start_date) : "\u2014"}
                {nextRdv.subject ? ` — ${nextRdv.subject}` : ""}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export function MutuellesCard({ mutuelles }: { mutuelles: ClientMutuelleInfo[] }) {
  const active = mutuelles.filter((m) => m.active);
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <ShieldCheck className="h-5 w-5 text-emerald-600" aria-hidden="true" />
        Mutuelle
      </h3>
      {active.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-4">
          Aucune mutuelle detectee ou renseignee.
        </p>
      ) : (
        <div className="space-y-3">
          {active.map((m) => (
            <div key={m.id} className="flex items-start gap-3 text-sm">
              <div className="min-w-0 flex-1">
                <p className="font-medium">{m.mutuelle_name}</p>
                <div className="flex flex-wrap gap-2 mt-1">
                  {m.numero_adherent && (
                    <span className="text-xs text-text-secondary">
                      N° adherent : {m.numero_adherent}
                    </span>
                  )}
                  <span
                    className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                      m.confidence >= 0.9
                        ? "bg-emerald-50 text-emerald-700"
                        : m.confidence >= 0.5
                          ? "bg-amber-50 text-amber-700"
                          : "bg-gray-100 text-gray-600"
                    }`}
                  >
                    Confiance : {Math.round(m.confidence * 100)}%
                  </span>
                  <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                    {m.source === "cosium_tpp"
                      ? "Tiers payant"
                      : m.source === "cosium_invoice"
                        ? "Facture"
                        : m.source === "manual"
                          ? "Saisie manuelle"
                          : m.source}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function CorrectionCard({ correction }: { correction: CorrectionActuelle }) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Correction actuelle</h3>
      <p className="text-xs text-text-secondary mb-3">
        {correction.prescription_date
          ? `Ordonnance du ${formatDate(correction.prescription_date)}`
          : "Date inconnue"}
        {correction.prescriber_name ? ` — Dr ${correction.prescriber_name}` : ""}
      </p>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-text-secondary text-xs">
            <th className="text-left font-medium py-1"></th>
            <th className="text-right font-medium py-1 px-2">Sph</th>
            <th className="text-right font-medium py-1 px-2">Cyl</th>
            <th className="text-right font-medium py-1 px-2">Axe</th>
            <th className="text-right font-medium py-1 px-2">Add</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          <tr>
            <td className="py-1 font-medium font-sans">OD</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.sphere_right)}</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.cylinder_right)}</td>
            <td className="text-right py-1 px-2">{formatAxis(correction.axis_right)}</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.addition_right)}</td>
          </tr>
          <tr>
            <td className="py-1 font-medium font-sans">OG</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.sphere_left)}</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.cylinder_left)}</td>
            <td className="text-right py-1 px-2">{formatAxis(correction.axis_left)}</td>
            <td className="text-right py-1 px-2">{formatDiopter(correction.addition_left)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export function RecentInteractionsCard({ interactions }: { interactions: Interaction[] }) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Dernieres interactions</h3>
      {interactions.length === 0 ? (
        <p className="text-sm text-text-secondary text-center py-4">Aucune interaction</p>
      ) : (
        <div className="space-y-3">
          {interactions.slice(0, 5).map((i) => {
            const Icon = TYPE_ICONS[i.type] || Pencil;
            return (
              <div key={i.id} className="flex items-start gap-3 text-sm">
                <Icon className="h-4 w-4 text-text-secondary mt-0.5 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{i.subject}</p>
                  <p className="text-xs text-text-secondary">
                    <DateDisplay date={i.created_at} />
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
