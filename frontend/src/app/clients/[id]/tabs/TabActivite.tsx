"use client";

import { useMemo } from "react";
import useSWR from "swr";
import { LoadingState } from "@/components/ui/LoadingState";
import { formatDateTime, formatMoney } from "@/lib/format";
import {
  FileText,
  CreditCard,
  Calendar,
  Pencil,
  Shield,
  FolderOpen,
  Activity,
  PhoneCall,
  Mail,
  MessageSquare,
  Eye,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface AuditLogEntry {
  id: number;
  user_id: number;
  action: string;
  entity_type: string;
  entity_id: number;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
}

interface Interaction {
  id: number;
  type: string;
  direction: string;
  subject: string;
  content: string | null;
  created_at: string;
}

interface Devis {
  id: number;
  numero: string;
  statut: string;
  montant_ttc: number;
  reste_a_charge: number;
}

interface Facture {
  id: number;
  numero: string;
  statut: string;
  montant_ttc: number;
  date_emission: string;
}

interface Paiement {
  id: number;
  payeur: string;
  mode: string | null;
  montant_du: number;
  montant_paye: number;
  statut: string;
}

interface TimelineEvent {
  id: string;
  date: string;
  icon: React.ComponentType<{ className?: string }>;
  iconColor: string;
  title: string;
  detail: string;
  category: string;
}

/* ------------------------------------------------------------------ */
/*  Icon mapping                                                       */
/* ------------------------------------------------------------------ */

const INTERACTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  appel: PhoneCall,
  email: Mail,
  sms: MessageSquare,
  visite: Eye,
  note: Pencil,
  tache: Calendar,
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface TabActiviteProps {
  clientId: string | number;
  interactions: Interaction[];
  devis: Devis[];
  factures: Facture[];
  paiements: Paiement[];
}

export function TabActivite({
  clientId,
  interactions,
  devis,
  factures,
  paiements,
}: TabActiviteProps) {
  const { data: auditLogs, isLoading: auditLoading } = useSWR<AuditLogEntry[]>(
    `/audit-logs?entity_type=customer&entity_id=${clientId}&limit=20`
  );

  const timeline = useMemo(() => {
    const events: TimelineEvent[] = [];

    // Interactions
    for (const i of interactions ?? []) {
      const Icon = INTERACTION_ICONS[i.type] || Pencil;
      events.push({
        id: `int-${i.id}`,
        date: i.created_at,
        icon: Icon,
        iconColor: "text-blue-500",
        title: i.subject,
        detail: i.type === "note" ? "Note ajoutee" : `${i.type} — ${i.direction}`,
        category: "interaction",
      });
    }

    // Devis
    for (const d of devis ?? []) {
      events.push({
        id: `devis-${d.id}`,
        date: new Date().toISOString(), // devis don't always have a date field
        icon: FileText,
        iconColor: "text-amber-500",
        title: `Devis ${d.numero} cree (${formatMoney(d.montant_ttc)})`,
        detail: `Statut : ${d.statut} — Reste a charge : ${formatMoney(d.reste_a_charge)}`,
        category: "devis",
      });
    }

    // Factures
    for (const f of factures ?? []) {
      events.push({
        id: `fac-${f.id}`,
        date: f.date_emission,
        icon: FileText,
        iconColor: "text-purple-500",
        title: `Facture ${f.numero} (${formatMoney(f.montant_ttc)})`,
        detail: `Statut : ${f.statut}`,
        category: "facture",
      });
    }

    // Paiements
    for (const p of paiements ?? []) {
      events.push({
        id: `pay-${p.id}`,
        date: new Date().toISOString(),
        icon: CreditCard,
        iconColor: "text-emerald-500",
        title: `Paiement recu (${formatMoney(p.montant_paye)})`,
        detail: `${p.payeur}${p.mode ? ` — ${p.mode}` : ""} — ${p.statut}`,
        category: "paiement",
      });
    }

    // Audit logs
    for (const a of auditLogs ?? []) {
      events.push({
        id: `audit-${a.id}`,
        date: a.created_at,
        icon: a.entity_type === "case" ? FolderOpen : a.entity_type === "pec" ? Shield : Activity,
        iconColor: "text-gray-400",
        title: `${a.action} sur ${a.entity_type} #${a.entity_id}`,
        detail: "",
        category: "audit",
      });
    }

    // Sort by date descending
    events.sort((a, b) => {
      const da = new Date(a.date).getTime();
      const db = new Date(b.date).getTime();
      if (isNaN(da) && isNaN(db)) return 0;
      if (isNaN(da)) return 1;
      if (isNaN(db)) return -1;
      return db - da;
    });

    return events.slice(0, 50);
  }, [interactions, devis, factures, paiements, auditLogs]);

  if (auditLoading) {
    return <LoadingState text="Chargement de l'activite..." />;
  }

  if (timeline.length === 0) {
    return (
      <div className="text-center py-12">
        <Activity className="mx-auto h-8 w-8 text-gray-300 mb-3" />
        <p className="text-sm text-text-secondary">
          Aucune activite recente pour ce client.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">
        Activite recente
      </h3>
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-4">
          {timeline.map((event) => {
            const Icon = event.icon;
            return (
              <div key={event.id} className="relative flex items-start gap-4 pl-2">
                <div className="relative z-10 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white border border-gray-200">
                  <Icon className={`h-4 w-4 ${event.iconColor}`} />
                </div>
                <div className="flex-1 min-w-0 pt-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {event.title}
                  </p>
                  {event.detail && (
                    <p className="text-xs text-text-secondary mt-0.5">
                      {event.detail}
                    </p>
                  )}
                  <p className="text-xs text-gray-400 mt-0.5">
                    {formatDateTime(event.date)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
