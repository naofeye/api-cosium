"use client";

import { DateDisplay } from "@/components/ui/DateDisplay";
import { formatPhone } from "@/lib/format";
import {
  User,
  Phone,
  Mail,
  MapPin,
  Shield,
  RefreshCw,
  Pencil,
  PhoneCall,
  MessageSquare,
  Eye,
  Calendar,
} from "lucide-react";
import Link from "next/link";

interface Interaction {
  id: number;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_at: string;
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
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <Icon className="h-4 w-4 text-text-secondary shrink-0" />
      <div className="flex justify-between flex-1">
        <span className="text-text-secondary">{label}</span>
        <span className="font-medium">{value}</span>
      </div>
    </div>
  );
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
}: TabResumeProps) {
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
            Voir les opportunites →
          </Link>
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold mb-4">Informations personnelles</h3>
          <div className="space-y-3 text-sm">
            <InfoRow icon={User} label="Nom" value={`${firstName} ${lastName}`} />
            <InfoRow icon={Phone} label="Telephone" value={phone ? formatPhone(phone) : "Non renseigne"} />
            <InfoRow icon={Mail} label="Email" value={email || "Non renseigne"} />
            <InfoRow icon={Shield} label="N° Secu" value={socialSecurityNumber || "Non renseigne"} />
            <InfoRow icon={MapPin} label="Ville" value={city ? `${postalCode || ""} ${city}` : "Non renseignee"} />
          </div>
        </div>
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
    </div>
  );
}
