"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { fetchJson } from "@/lib/api";
import { downloadPdf } from "@/lib/download";
import { formatMoney } from "@/lib/format";
import { Euro, FileText, ShieldCheck, Heart, Download } from "lucide-react";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";

interface DevisLigne {
  id: number;
  designation: string;
  quantite: number;
  prix_unitaire_ht: number;
  taux_tva: number;
  montant_ht: number;
  montant_ttc: number;
}

interface DevisDetail {
  id: number;
  case_id: number;
  numero: string;
  status: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  part_secu: number;
  part_mutuelle: number;
  reste_a_charge: number;
  created_at: string;
  updated_at: string | null;
  lignes: DevisLigne[];
  customer_name: string | null;
}

const NEXT_STATUSES: Record<string, { label: string; status: string; variant: "primary" | "outline" | "danger" }[]> = {
  brouillon: [
    { label: "Envoyer au client", status: "envoye", variant: "primary" },
    { label: "Annuler", status: "annule", variant: "danger" },
  ],
  envoye: [
    { label: "Marquer comme signe", status: "signe", variant: "primary" },
    { label: "Annuler", status: "annule", variant: "danger" },
  ],
  signe: [
    { label: "Facturer", status: "facture", variant: "primary" },
    { label: "Annuler", status: "annule", variant: "danger" },
  ],
  facture: [],
  annule: [],
};

export default function DevisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: devis, error: swrError, isLoading, mutate } = useSWR<DevisDetail>(`/devis/${id}`);
  const [changing, setChanging] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const changeStatus = async (newStatus: string) => {
    if (changing) return;
    setChanging(true);
    try {
      const updated = await fetchJson<DevisDetail>(`/devis/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      mutate({ ...devis!, status: updated.status }, false);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setChanging(false);
    }
  };

  if (isLoading) {
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "..." }]}>
        <LoadingState text="Chargement du devis..." />
      </PageLayout>
    );
  }

  if (swrError?.message?.includes("introuvable") || swrError?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Introuvable" }]}>
        <EmptyState
          title="Devis introuvable"
          description="Ce devis n'existe pas ou a ete supprime."
          action={
            <Link href="/devis">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }

  const error = swrError?.message ?? mutationError ?? null;

  if (error || !devis) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Erreur" }]}>
        <ErrorState message={error || "Devis introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );
  }

  const generateFacture = async () => {
    if (generating) return;
    setGenerating(true);
    try {
      const resp = await fetchJson<{ id: number }>("/factures", {
        method: "POST",
        body: JSON.stringify({ devis_id: devis.id }),
      });
      router.push(`/factures/${resp.id}`);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la generation");
      setGenerating(false);
    }
  };

  const actions = NEXT_STATUSES[devis.status] || [];

  return (
    <PageLayout
      title={`Devis ${devis.numero}`}
      breadcrumb={[{ label: "Devis", href: "/devis" }, { label: devis.numero }]}
      actions={
        <div className="flex items-center gap-2">
          <StatusBadge status={devis.status} />
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadPdf(`/devis/${devis.id}/pdf`, `devis_${devis.numero}.pdf`)}
          >
            <Download className="h-4 w-4" /> PDF
          </Button>
          {devis.status === "signe" && (
            <Button onClick={generateFacture} disabled={generating}>
              {generating ? "Generation..." : "Generer la facture"}
            </Button>
          )}
          {actions.map((a) => (
            <Button
              key={a.status}
              variant={a.variant}
              onClick={() => (a.status === "annule" ? setConfirmCancel(true) : changeStatus(a.status))}
              disabled={changing}
            >
              {a.label}
            </Button>
          ))}
        </div>
      }
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard icon={Euro} label="Total TTC" value={formatMoney(devis.montant_ttc)} color="primary" />
        <KPICard icon={ShieldCheck} label="Part Secu" value={formatMoney(devis.part_secu)} color="info" />
        <KPICard icon={Heart} label="Part Mutuelle" value={formatMoney(devis.part_mutuelle)} color="info" />
        <KPICard
          icon={FileText}
          label="Reste a charge"
          value={formatMoney(devis.reste_a_charge)}
          color={devis.reste_a_charge > 0 ? "danger" : "success"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Informations</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-text-secondary">Client</span>
              <span className="font-medium">{devis.customer_name || "-"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Dossier</span>
              <a href={`/cases/${devis.case_id}`} className="text-primary hover:underline">
                #{devis.case_id}
              </a>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">Date de creation</span>
              <DateDisplay date={devis.created_at} />
            </div>
            {devis.updated_at && (
              <div className="flex justify-between">
                <span className="text-text-secondary">Derniere modification</span>
                <DateDisplay date={devis.updated_at} />
              </div>
            )}
          </div>
        </div>
        <div className="lg:col-span-2 rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-3">Recapitulatif financier</h3>
          <div className="space-y-2 text-sm max-w-sm ml-auto">
            <div className="flex justify-between">
              <span className="text-text-secondary">Total HT</span>
              <span className="font-medium tabular-nums">{formatMoney(devis.montant_ht)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary">TVA</span>
              <span className="font-medium tabular-nums">{formatMoney(devis.tva)}</span>
            </div>
            <div className="flex justify-between border-t border-border pt-2">
              <span className="font-semibold">Total TTC</span>
              <span className="font-bold tabular-nums">{formatMoney(devis.montant_ttc)}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Part Secu</span>
              <span className="tabular-nums">- {formatMoney(devis.part_secu)}</span>
            </div>
            <div className="flex justify-between text-text-secondary">
              <span>Part Mutuelle</span>
              <span className="tabular-nums">- {formatMoney(devis.part_mutuelle)}</span>
            </div>
            <div className="flex justify-between border-t border-border pt-2">
              <span className="font-semibold text-danger">Reste a charge</span>
              <span className="font-bold tabular-nums text-danger">{formatMoney(devis.reste_a_charge)}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-bg-card shadow-sm">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">Lignes du devis ({devis.lignes.length})</h3>
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
            {devis.lignes.map((l) => (
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
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(devis.montant_ht)}</td>
              <td className="px-4 py-3 text-right tabular-nums">{formatMoney(devis.montant_ttc)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <ConfirmDialog
        open={confirmCancel}
        title="Annuler ce devis"
        message="Etes-vous sur de vouloir annuler ce devis ? Cette action est irreversible."
        confirmLabel="Annuler le devis"
        danger
        onConfirm={() => {
          setConfirmCancel(false);
          changeStatus("annule");
        }}
        onCancel={() => setConfirmCancel(false)}
      />
    </PageLayout>
  );
}
