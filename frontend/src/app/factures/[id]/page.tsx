"use client";

import { useParams } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { downloadPdf } from "@/lib/download";
import { formatMoney } from "@/lib/format";
import { Euro, FileText, Receipt, Download } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";

interface FactureLigne {
  id: number;
  designation: string;
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
  montant_ht: number;
  montant_ttc: number;
}

interface FactureDetail {
  id: number;
  case_id: number;
  devis_id: number;
  numero: string;
  date_emission: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  status: string;
  created_at: string;
  customer_name: string | null;
  devis_numero: string | null;
  lignes: FactureLigne[];
}

export default function FactureDetailPage() {
  const params = useParams();
  const id = params.id as string;

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
            onClick={() => downloadPdf(`/factures/${facture.id}/pdf`, `facture_${facture.numero}.pdf`)}
          >
            <Download className="h-4 w-4" /> PDF
          </Button>
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <KPICard icon={Euro} label="Montant TTC" value={formatMoney(facture.montant_ttc)} color="primary" />
        <KPICard icon={FileText} label="Montant HT" value={formatMoney(facture.montant_ht)} color="info" />
        <KPICard icon={Receipt} label="TVA" value={formatMoney(facture.tva)} color="info" />
      </div>

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

      <div className="rounded-xl border border-border bg-bg-card shadow-sm">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">Lignes ({(facture.lignes ?? []).length})</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-gray-50">
              <th scope="col" className="px-4 py-3 text-left font-medium text-text-secondary">Designation</th>
              <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">Qte</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">PU HT</th>
              <th scope="col" className="px-4 py-3 text-center font-medium text-text-secondary">TVA %</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">HT</th>
              <th scope="col" className="px-4 py-3 text-right font-medium text-text-secondary">TTC</th>
            </tr>
          </thead>
          <tbody>
            {(facture.lignes ?? []).map((l) => (
              <tr key={l.id} className="border-b border-border last:border-0">
                <td className="px-4 py-3 font-medium">{l.designation}</td>
                <td className="px-4 py-3 text-center">{l.quantite}</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatMoney(l.prix_unitaire_ht)}</td>
                <td className="px-4 py-3 text-center">{l.taux_tva}%</td>
                <td className="px-4 py-3 text-right tabular-nums">{formatMoney(l.montant_ht)}</td>
                <td className="px-4 py-3 text-right tabular-nums font-medium">{formatMoney(l.montant_ttc)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="bg-gray-50 font-semibold">
              <td colSpan={4} className="px-4 py-3">
                Total
              </td>
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(facture.montant_ht)}</td>
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(facture.montant_ttc)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </PageLayout>
  );
}
