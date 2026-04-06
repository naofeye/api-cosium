"use client";

import { useState, useMemo } from "react";
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
import { formatMoney, formatDate } from "@/lib/format";
import {
  Euro,
  FileText,
  ShieldCheck,
  Heart,
  Download,
  Send,
  CheckCircle,
  XCircle,
  Receipt,
  Copy,
  Edit,
  Eye,
  ArrowRight,
  Check,
  Printer,
} from "lucide-react";
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
  sent_at?: string | null;
  signed_at?: string | null;
  invoiced_at?: string | null;
  facture_id?: number | null;
  lignes: DevisLigne[];
  customer_name: string | null;
}

/* ─── Status Timeline ─── */

interface TimelineStep {
  key: string;
  label: string;
  dateField: keyof DevisDetail;
}

const TIMELINE_STEPS: TimelineStep[] = [
  { key: "brouillon", label: "Brouillon", dateField: "created_at" },
  { key: "envoye", label: "Envoye", dateField: "sent_at" },
  { key: "signe", label: "Signe", dateField: "signed_at" },
  { key: "facture", label: "Facture", dateField: "invoiced_at" },
];

const STATUS_ORDER: Record<string, number> = {
  brouillon: 0,
  envoye: 1,
  signe: 2,
  facture: 3,
  annule: -1,
  refuse: -1,
};

function DevisTimeline({ devis }: { devis: DevisDetail }) {
  const currentIdx = STATUS_ORDER[devis.status] ?? -1;
  const isTerminal = devis.status === "annule" || devis.status === "refuse";

  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
      <h3 className="text-sm font-semibold text-text-secondary uppercase tracking-wider mb-4">
        Progression du devis
      </h3>
      {isTerminal ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100">
            <XCircle className="h-5 w-5 text-red-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-red-700 capitalize">{devis.status.replace(/_/g, " ")}</p>
            {devis.updated_at && (
              <p className="text-xs text-text-secondary">{formatDate(devis.updated_at)}</p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-0">
          {TIMELINE_STEPS.map((step, idx) => {
            const stepIdx = idx;
            const isCompleted = stepIdx < currentIdx;
            const isCurrent = stepIdx === currentIdx;
            const dateValue = devis[step.dateField];
            const dateStr = typeof dateValue === "string" ? dateValue : null;

            return (
              <div key={step.key} className="flex items-center flex-1 last:flex-none">
                <div className="flex flex-col items-center min-w-0">
                  <div
                    className={`flex items-center justify-center w-9 h-9 rounded-full border-2 transition-colors ${
                      isCompleted
                        ? "bg-emerald-600 border-emerald-600"
                        : isCurrent
                          ? "bg-blue-600 border-blue-600"
                          : "bg-white border-gray-300"
                    }`}
                  >
                    {isCompleted ? (
                      <Check className="h-4 w-4 text-white" />
                    ) : isCurrent ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-white" />
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-gray-300" />
                    )}
                  </div>
                  <p
                    className={`mt-2 text-xs font-medium ${
                      isCompleted ? "text-emerald-700" : isCurrent ? "text-blue-700" : "text-text-secondary"
                    }`}
                  >
                    {step.label}
                  </p>
                  {dateStr && (
                    <p className="text-[10px] text-text-secondary mt-0.5">{formatDate(dateStr)}</p>
                  )}
                </div>
                {idx < TIMELINE_STEPS.length - 1 && (
                  <div className="flex-1 mx-2 mt-[-1.5rem]">
                    <div
                      className={`h-0.5 w-full ${
                        stepIdx < currentIdx ? "bg-emerald-500" : "bg-gray-200"
                      }`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ─── Page ─── */

export default function DevisDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const { data: devis, error: swrError, isLoading, mutate } = useSWR<DevisDetail>(`/devis/${id}`);
  const [changing, setChanging] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [duplicating, setDuplicating] = useState(false);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [confirmRefuse, setConfirmRefuse] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);

  const changeStatus = async (newStatus: string) => {
    if (changing) return;
    setChanging(true);
    setMutationError(null);
    try {
      await fetchJson<DevisDetail>(`/devis/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      mutate();
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setChanging(false);
    }
  };

  const generateFacture = async () => {
    if (generating) return;
    setGenerating(true);
    setMutationError(null);
    try {
      const resp = await fetchJson<{ id: number }>("/factures", {
        method: "POST",
        body: JSON.stringify({ devis_id: devis!.id }),
      });
      router.push(`/factures/${resp.id}`);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la generation");
      setGenerating(false);
    }
  };

  const duplicateDevis = async () => {
    if (duplicating || !devis) return;
    setDuplicating(true);
    setMutationError(null);
    try {
      const resp = await fetchJson<{ id: number }>(`/devis/${devis.id}/duplicate`, {
        method: "POST",
      });
      router.push(`/devis/${resp.id}`);
    } catch (err) {
      setMutationError(err instanceof Error ? err.message : "Erreur lors de la duplication");
      setDuplicating(false);
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

  if (error && !devis) {
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Devis", href: "/devis" }, { label: "Erreur" }]}>
        <ErrorState message={error || "Devis introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );
  }

  if (!devis) return null;

  /* ─── Context-sensitive action buttons ─── */
  const renderActions = () => {
    const buttons: React.ReactNode[] = [];

    // Always show status badge
    buttons.push(<StatusBadge key="badge" status={devis.status} />);

    // Print button
    buttons.push(
      <Button
        key="print"
        variant="outline"
        size="sm"
        onClick={() => window.print()}
        className="no-print"
        aria-label="Imprimer le devis"
      >
        <Printer className="h-4 w-4" /> Imprimer
      </Button>,
    );

    // PDF download always available
    buttons.push(
      <Button
        key="pdf"
        variant="outline"
        size="sm"
        onClick={() => downloadPdf(`/devis/${devis.id}/pdf`, `devis_${devis.numero}.pdf`)}
        aria-label="Telecharger en PDF"
      >
        <Download className="h-4 w-4" /> PDF
      </Button>,
    );

    // Duplicate always available
    buttons.push(
      <Button key="dup" variant="outline" size="sm" onClick={duplicateDevis} disabled={duplicating} aria-label="Dupliquer ce devis">
        <Copy className="h-4 w-4" /> {duplicating ? "Duplication..." : "Dupliquer"}
      </Button>,
    );

    // Status-dependent actions
    switch (devis.status) {
      case "brouillon":
        buttons.push(
          <Link key="edit" href={`/devis/${devis.id}/edit`}>
            <Button variant="outline" size="sm">
              <Edit className="h-4 w-4" /> Modifier
            </Button>
          </Link>,
        );
        buttons.push(
          <Button key="send" onClick={() => changeStatus("envoye")} disabled={changing}>
            <Send className="h-4 w-4" /> {changing ? "Envoi..." : "Envoyer au client"}
          </Button>,
        );
        buttons.push(
          <Button key="cancel" variant="danger" size="sm" onClick={() => setConfirmCancel(true)} disabled={changing}>
            Annuler
          </Button>,
        );
        break;

      case "envoye":
        buttons.push(
          <Button key="sign" onClick={() => changeStatus("signe")} disabled={changing}>
            <CheckCircle className="h-4 w-4" /> {changing ? "Mise a jour..." : "Marquer comme signe"}
          </Button>,
        );
        buttons.push(
          <Button key="refuse" variant="danger" size="sm" onClick={() => setConfirmRefuse(true)} disabled={changing}>
            <XCircle className="h-4 w-4" /> Marquer comme refuse
          </Button>,
        );
        break;

      case "signe":
        buttons.push(
          <Button key="facture" onClick={generateFacture} disabled={generating}>
            <Receipt className="h-4 w-4" /> {generating ? "Generation..." : "Generer la facture"}
          </Button>,
        );
        buttons.push(
          <Link key="pec" href={`/pec?case_id=${devis.case_id}`}>
            <Button variant="outline" size="sm">
              <ShieldCheck className="h-4 w-4" /> Preparer PEC
            </Button>
          </Link>,
        );
        break;

      case "facture":
        if (devis.facture_id) {
          buttons.push(
            <Link key="viewfact" href={`/factures/${devis.facture_id}`}>
              <Button variant="outline" size="sm">
                <Eye className="h-4 w-4" /> Voir la facture
              </Button>
            </Link>,
          );
        }
        break;
    }

    return <div className="flex items-center gap-2 flex-wrap">{buttons}</div>;
  };

  return (
    <PageLayout
      title={`Devis ${devis.numero}`}
      breadcrumb={[{ label: "Devis", href: "/devis" }, { label: devis.numero }]}
      actions={renderActions()}
    >
      {/* Mutation error banner */}
      {mutationError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 flex items-center gap-2">
          <XCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" /> {mutationError}
        </div>
      )}

      {/* Status timeline */}
      <DevisTimeline devis={devis} />

      {/* KPI cards */}
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
        {/* Info card */}
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

        {/* Financial summary */}
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

      {/* Lines table */}
      <div className="rounded-xl border border-border bg-bg-card shadow-sm">
        <div className="px-5 py-3 border-b border-border">
          <h3 className="text-sm font-semibold text-text-primary">Lignes du devis ({(devis.lignes ?? []).length})</h3>
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
            {(devis.lignes ?? []).map((l) => (
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

      {/* Confirm dialogs */}
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
      <ConfirmDialog
        open={confirmRefuse}
        title="Marquer comme refuse"
        message="Confirmer le refus de ce devis par le client ? Vous pourrez dupliquer le devis pour creer une nouvelle proposition."
        confirmLabel="Marquer comme refuse"
        danger
        onConfirm={() => {
          setConfirmRefuse(false);
          changeStatus("refuse");
        }}
        onCancel={() => setConfirmRefuse(false)}
      />
    </PageLayout>
  );
}
