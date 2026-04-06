"use client";

import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { formatPhone, formatMoney, formatDate } from "@/lib/format";
import {
  User,
  Phone,
  Mail,
  MapPin,
  Shield,
  ShieldCheck,
  RefreshCw,
  Pencil,
  PhoneCall,
  MessageSquare,
  Eye,
  Calendar,
  Euro,
  Activity,
} from "lucide-react";
import Link from "next/link";
import { CopyButton } from "@/components/ui/CopyButton";

interface Interaction {
  id: number;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_at: string;
}

interface CorrectionActuelle {
  prescription_date: string | null;
  prescriber_name: string | null;
  sphere_right: number | null;
  cylinder_right: number | null;
  axis_right: number | null;
  addition_right: number | null;
  sphere_left: number | null;
  cylinder_left: number | null;
  axis_left: number | null;
  addition_left: number | null;
}

interface CalendarEvent {
  id: number;
  start_date: string | null;
  subject: string;
  category_name: string;
  status: string;
  site_name: string | null;
}

interface ClientMutuelleInfo {
  id: number;
  mutuelle_name: string;
  active: boolean;
  source: string;
  confidence: number;
  numero_adherent: string | null;
  type_beneficiaire: string;
  date_debut: string | null;
  date_fin: string | null;
}

interface CosiumInvoice {
  cosium_id: number;
  invoice_number: string;
  invoice_date: string | null;
  type: string;
  total_ti: number;
  settled: boolean;
}

interface TabResumeProps {
  firstName: string;
  lastName: string;
  phone: string | null;
  email: string | null;
  socialSecurityNumber: string | null;
  postalCode: string | null;
  city: string | null;
  renewalEligible: boolean;
  renewalMonths: number;
  interactions: Interaction[];
  correction: CorrectionActuelle | null;
  totalCaCosium: number;
  lastVisitDate: string | null;
  nextRdv: CalendarEvent | null;
  cosiumInvoices: CosiumInvoice[];
  mutuelles: ClientMutuelleInfo[];
}

const TYPE_ICONS: Record<string, typeof PhoneCall> = {
  appel: PhoneCall,
  email: Mail,
  sms: MessageSquare,
  visite: Eye,
  note: Pencil,
  tache: Calendar,
};

function InfoRow({
  icon: Icon,
  label,
  value,
  copyValue,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  copyValue?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-text-secondary shrink-0" />
      <div className="flex justify-between flex-1">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium inline-flex items-center gap-1">
          {value}
          {copyValue && <CopyButton text={copyValue} label={label} />}
        </span>
      </div>
    </div>
  );
}

function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

function formatAxis(value: number | null): string {
  if (value === null || value === undefined) return "-";
  return `${value}\u00B0`;
}

export function TabResume({
  firstName,
  lastName,
  phone,
  email,
  socialSecurityNumber,
  postalCode,
  city,
  renewalEligible,
  renewalMonths,
  interactions,
  correction,
  totalCaCosium,
  lastVisitDate,
  nextRdv,
  cosiumInvoices,
  mutuelles,
}: TabResumeProps) {
  const recentInvoices = cosiumInvoices?.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      {renewalEligible && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <RefreshCw className="h-5 w-5 text-amber-600 shrink-0" />
          <div className="flex-1">
            <p className="text-sm font-medium text-amber-900">Eligible au renouvellement</p>
            <p className="text-xs text-amber-700">
              Dernier equipement achete il y a {renewalMonths} mois. Pensez a proposer un renouvellement.
            </p>
          </div>
          <Link href="/renewals" className="text-xs font-medium text-amber-700 hover:underline whitespace-nowrap">
            Voir les opportunites &rarr;
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Personal info */}
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Informations personnelles</h3>
          <div className="space-y-3 text-sm">
            <InfoRow icon={User} label="Nom" value={`${firstName} ${lastName}`} />
            <InfoRow icon={Phone} label="Telephone" value={phone ? formatPhone(phone) : "Non renseigne"} copyValue={phone || undefined} />
            <InfoRow icon={Mail} label="Email" value={email || "Non renseigne"} copyValue={email || undefined} />
            <InfoRow icon={Shield} label="N\u00B0 Secu" value={socialSecurityNumber || "Non renseigne"} copyValue={socialSecurityNumber || undefined} />
            <InfoRow icon={MapPin} label="Ville" value={city ? `${postalCode || ""} ${city}` : "Non renseignee"} />
          </div>
        </div>

        {/* Financial + visit summary */}
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

        {/* Mutuelle */}
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 text-emerald-600" aria-hidden="true" />
            Mutuelle
          </h3>
          {mutuelles.length === 0 ? (
            <p className="text-sm text-text-secondary text-center py-4">
              Aucune mutuelle detectee ou renseignee.
            </p>
          ) : (
            <div className="space-y-3">
              {mutuelles.filter(m => m.active).map((m) => (
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

        {/* Latest correction */}
        {correction && (
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
        )}

        {/* Latest interactions */}
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
      </div>

      {/* Recent Cosium invoices */}
      {recentInvoices.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-card shadow-sm">
          <div className="px-6 py-3 border-b">
            <h3 className="text-sm font-semibold">Dernieres factures Cosium</h3>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-text-secondary">
                <th className="px-4 py-2 text-left font-medium">Numero</th>
                <th className="px-4 py-2 text-left font-medium">Date</th>
                <th className="px-4 py-2 text-left font-medium">Type</th>
                <th className="px-4 py-2 text-right font-medium">Montant TTC</th>
                <th className="px-4 py-2 text-center font-medium">Solde</th>
              </tr>
            </thead>
            <tbody>
              {recentInvoices.map((inv) => (
                <tr key={inv.cosium_id} className="border-b last:border-0">
                  <td className="px-4 py-2 font-mono">{inv.invoice_number}</td>
                  <td className="px-4 py-2">
                    {inv.invoice_date ? <DateDisplay date={inv.invoice_date} /> : "-"}
                  </td>
                  <td className="px-4 py-2">{inv.type}</td>
                  <td className="px-4 py-2 text-right">
                    <MoneyDisplay amount={inv.total_ti} bold />
                  </td>
                  <td className="px-4 py-2 text-center">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        inv.settled
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {inv.settled ? "Solde" : "Non solde"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
