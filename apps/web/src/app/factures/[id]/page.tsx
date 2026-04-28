"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { SendDocumentEmailDialog } from "@/components/ui/SendDocumentEmailDialog";
import { downloadPdf } from "@/lib/download";
import { formatMoney } from "@/lib/format";
import { Euro, FileText, Receipt, Download, Printer, Mail, ShieldCheck, AlertCircle } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";
import type { FactureDetail } from "./types";
import { FacturePaymentsTable } from "./components/FacturePaymentsTable";
import { FactureLignesTable } from "./components/FactureLignesTable";

export default function FactureDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [emailOpen, setEmailOpen] = useState(false);

  const { data: facture, error, isLoading, mutate } = useSWR<FactureDetail>(`/factures/${id}`);

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Factures", href: "/factures" }, { label: "..." }]}>
        <LoadingState text="Chargement de la facture..." />
      </PageLayout>
    );
  }

  if (error?.message?.includes("introuvable") || error?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "Factures", href: "/factures" }, { label: "Introuvable" }]}>
        <EmptyState
          title="Facture introuvable"
          description="Cette facture n'existe pas ou a ete supprimee."
          action={
            <Link href="/factures">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  if (error || !facture) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Factures", href: "/factures" }, { label: "Erreur" }]}>
        <ErrorState message={error?.message ?? "Facture introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );
  }

  const resteAPayer = facture.reste_a_payer ?? (facture.montant_ttc - (facture.montant_paye ?? 0));

  return (
    <PageLayout
      title={`Facture ${facture.numero}`}
      breadcrumb={[{ label: "Factures", href: "/factures" }, { label: facture.numero }]}
      actions={
        <div className="flex items-center gap-2">
          <StatusBadge status={facture.status} />
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.print()}
            className="no-print"
            aria-label="Imprimer la facture"
          >
            <Printer className="h-4 w-4" /> Imprimer
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadPdf(`/factures/${facture.id}/pdf`, `facture_${facture.numero}.pdf`)}
            aria-label="Telecharger en PDF"
          >
            <Download className="h-4 w-4" /> PDF
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEmailOpen(true)}
            aria-label="Envoyer la facture par email"
          >
            <Mail className="h-4 w-4" /> Envoyer par email
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={Euro} label="Montant TTC" value={formatMoney(facture.montant_ttc)} color="primary" />
        <KPICard icon={FileText} label="Montant HT" value={formatMoney(facture.montant_ht)} color="info" />
        <KPICard icon={Receipt} label="TVA" value={formatMoney(facture.tva)} color="info" />
        <KPICard
          icon={AlertCircle}
          label="Reste a payer"
          value={formatMoney(resteAPayer)}
          color={resteAPayer > 0 ? "danger" : "success"}
        />
      </div>

      {/* Remaining balance banner */}
      {resteAPayer > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600 shrink-0" />
            <div>
              <p className="text-sm font-semibold text-amber-800">
                Solde restant : {formatMoney(resteAPayer)}
              </p>
              <p className="text-xs text-amber-600">
                Cette facture n&apos;est pas entièrement reglee.
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const subject = encodeURIComponent(`Facture ${facture.numero} - Solde restant`);
              const body = encodeURIComponent(
                `Bonjour,\n\nNous vous informons qu'un solde de ${formatMoney(resteAPayer)} reste a regler pour la facture ${facture.numero}.\n\nCordialement,\nOptiFlow`
              );
              const email = facture.customer_email || "";
              window.open(`mailto:${email}?subject=${subject}&body=${body}`, "_self");
            }}
            aria-label="Envoyer un rappel au client"
          >
            <Mail className="h-4 w-4 mr-1" /> Envoyer au client
          </Button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Informations</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Client</span>
              <span className="font-medium">{facture.customer_name || "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Dossier</span>
              <a href={`/cases/${facture.case_id}`} className="text-primary hover:underline">
                #{facture.case_id}
              </a>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Devis</span>
              <a href={`/devis/${facture.devis_id}`} className="text-primary hover:underline">
                {facture.devis_numero || `#${facture.devis_id}`}
              </a>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Date emission</span>
              <DateDisplay date={facture.date_emission} />
            </div>
          </div>
        </div>
        <div className="lg:col-span-2 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Recapitulatif</h3>
          <div className="space-y-2 text-sm max-w-sm ml-auto">
            <div className="flex justify-between">
              <span className="text-text-secondary">Total HT</span>
              <span className="font-medium tabular-nums">{formatMoney(facture.montant_ht)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">TVA</span>
              <span className="font-medium tabular-nums">{formatMoney(facture.tva)}</span>
            </div>
            <div className="flex justify-between border-t border-border pt-2">
              <span className="font-bold">Total TTC</span>
              <span className="font-bold tabular-nums">{formatMoney(facture.montant_ttc)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* PEC associee */}
      {facture.pec && (
        <div className="rounded-xl border border-border bg-bg-card p-4 mb-6 shadow-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-primary" />
              <div>
                <p className="text-sm font-semibold text-text-primary">
                  Prise en charge associee
                </p>
                <p className="text-xs text-text-secondary">
                  {facture.pec.organisme} — Demande : {formatMoney(facture.pec.montant_demande)}
                  {facture.pec.montant_accepte !== null && ` — Accepte : ${formatMoney(facture.pec.montant_accepte)}`}
                </p>
              </div>
            </div>
            <Link href={`/pec/${facture.pec.id}`}>
              <Button variant="outline" size="sm">Voir la PEC</Button>
            </Link>
          </div>
        </div>
      )}

      <FacturePaymentsTable payments={facture.payments ?? []} />
      <FactureLignesTable
        lignes={facture.lignes ?? []}
        montant_ht={facture.montant_ht}
        montant_ttc={facture.montant_ttc}
      />

      <SendDocumentEmailDialog
        open={emailOpen}
        onClose={() => setEmailOpen(false)}
        endpoint={`/factures/${facture.id}/send-email`}
        documentNumero={facture.numero}
        documentLabel="facture"
        defaultRecipient={facture.customer_email ?? null}
      />
    </PageLayout>
  );
}
