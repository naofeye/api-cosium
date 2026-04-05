"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { KPICard } from "@/components/ui/KPICard";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import { Euro, CheckCircle, Clock, FolderOpen, Plus, Trash2, Download, Eye, Calendar } from "lucide-react";
import { downloadPdf } from "@/lib/download";
import { EmptyState } from "@/components/ui/EmptyState";
import Link from "next/link";
import { AvatarUpload } from "./components/AvatarUpload";

import { TabResume } from "./tabs/TabResume";
import { TabDossiers } from "./tabs/TabDossiers";
import { TabFinances } from "./tabs/TabFinances";
import { TabDocuments } from "./tabs/TabDocuments";
import { TabMarketing } from "./tabs/TabMarketing";
import { TabHistorique } from "./tabs/TabHistorique";
import { TabCosiumDocuments } from "./tabs/TabCosiumDocuments";
import { TabOrdonnances } from "./tabs/TabOrdonnances";
import { TabCosiumPaiements } from "./tabs/TabCosiumPaiements";
import { TabRendezVous } from "./tabs/TabRendezVous";
import { TabEquipements } from "./tabs/TabEquipements";

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

interface CosiumPrescriptionSummary {
  id: number;
  cosium_id: number;
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
  spectacles_json: string | null;
}

interface CosiumPaymentSummary {
  id: number;
  cosium_id: number;
  amount: number;
  type: string;
  due_date: string | null;
  issuer_name: string;
  bank: string;
  site_name: string;
  payment_number: string;
  invoice_cosium_id: number | null;
}

interface CosiumCalendarSummary {
  id: number;
  cosium_id: number;
  start_date: string | null;
  end_date: string | null;
  subject: string;
  category_name: string;
  category_color: string;
  status: string;
  canceled: boolean;
  missed: boolean;
  observation: string | null;
  site_name: string | null;
}

interface EquipmentItem {
  prescription_id: number;
  prescription_date: string | null;
  label: string;
  brand: string;
  type: string;
}

interface CosiumDataBundle {
  prescriptions: CosiumPrescriptionSummary[];
  cosium_payments: CosiumPaymentSummary[];
  calendar_events: CosiumCalendarSummary[];
  equipments: EquipmentItem[];
  correction_actuelle: CorrectionActuelle | null;
  total_ca_cosium: number;
  last_visit_date: string | null;
  customer_tags: string[];
}

interface Client360 {
  id: number;
  first_name: string;
  last_name: string;
  email: string | null;
  phone: string | null;
  birth_date: string | null;
  address: string | null;
  city: string | null;
  postal_code: string | null;
  social_security_number: string | null;
  avatar_url: string | null;
  cosium_id: string | number | null;
  created_at: string | null;
  dossiers: { id: number; statut: string; source: string; created_at: string }[];
  devis: { id: number; numero: string; statut: string; montant_ttc: number; reste_a_charge: number }[];
  factures: { id: number; numero: string; statut: string; montant_ttc: number; date_emission: string }[];
  paiements: {
    id: number;
    payeur: string;
    mode: string | null;
    montant_du: number;
    montant_paye: number;
    statut: string;
  }[];
  documents: { id: number; type: string; filename: string; uploaded_at: string }[];
  pec: { id: number; statut: string; montant_demande: number; montant_accorde: number | null }[];
  consentements: { canal: string; consenti: boolean }[];
  interactions: {
    id: number;
    type: string;
    direction: string;
    subject: string;
    content: string | null;
    created_at: string;
  }[];
  cosium_invoices: {
    cosium_id: number;
    invoice_number: string;
    invoice_date: string | null;
    type: string;
    total_ti: number;
    outstanding_balance: number;
    share_social_security: number;
    share_private_insurance: number;
    settled: boolean;
  }[];
  cosium_data: CosiumDataBundle;
  resume_financier: { total_facture: number; total_paye: number; reste_du: number; taux_recouvrement: number };
}

type Tab =
  | "resume"
  | "dossiers"
  | "finances"
  | "documents"
  | "marketing"
  | "historique"
  | "cosium-docs"
  | "ordonnances"
  | "cosium-paiements"
  | "rendez-vous"
  | "equipements";

function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

export default function ClientDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const id = params.id as string;

  const { data, error: swrError, isLoading, mutate } = useSWR<Client360>(`/clients/${id}/360`);

  const [activeTab, setActiveTab] = useState<Tab>("resume");
  const [showDelete, setShowDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [intType, setIntType] = useState("note");
  const [intDir, setIntDir] = useState("interne");
  const [intSubj, setIntSubj] = useState("");
  const [intBody, setIntBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const { renewalEligible, renewalMonths } = useMemo(() => {
    if (!data || data.factures.length === 0) return { renewalEligible: false, renewalMonths: 0 };
    const dates = data.factures.map((f) => new Date(f.date_emission).getTime());
    const lastDate = Math.max(...dates);
    const months = Math.floor((Date.now() - lastDate) / (30 * 24 * 60 * 60 * 1000));
    return { renewalEligible: months >= 24, renewalMonths: months };
  }, [data]);

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await fetchJson(`/clients/${id}`, { method: "DELETE" });
      toast("Client supprime", "success");
      router.push("/clients");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur", "error");
    } finally {
      setDeleting(false);
      setShowDelete(false);
    }
  };

  const addInteraction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || !intSubj.trim()) return;
    setSubmitting(true);
    try {
      await fetchJson("/interactions", {
        method: "POST",
        body: JSON.stringify({
          client_id: Number(id),
          type: intType,
          direction: intDir,
          subject: intSubj,
          content: intBody || null,
        }),
      });
      setShowForm(false);
      setIntSubj("");
      setIntBody("");
      mutate();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Erreur", "error");
    } finally {
      setSubmitting(false);
    }
  };

  if (isLoading)
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Clients", href: "/clients" }, { label: "..." }]}>
        <LoadingState text="Chargement du client..." />
      </PageLayout>
    );
  if (swrError?.message?.includes("introuvable") || swrError?.message?.includes("404")) {
    return (
      <PageLayout title="Introuvable" breadcrumb={[{ label: "Clients", href: "/clients" }, { label: "Introuvable" }]}>
        <EmptyState
          title="Client introuvable"
          description="Ce client n'existe pas ou a ete supprime."
          action={
            <Link href="/clients">
              <Button>Retour a la liste</Button>
            </Link>
          }
        />
      </PageLayout>
    );
  }
  if (swrError || !data)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Clients", href: "/clients" }, { label: "Erreur" }]}>
        <ErrorState message={swrError?.message ?? "Client introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );

  const fin = data.resume_financier;
  const cd = data.cosium_data;
  const correction = cd?.correction_actuelle;

  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "resume", label: "Resume" },
    { key: "dossiers", label: "Dossiers", count: data.dossiers.length },
    { key: "finances", label: "Finances", count: data.factures.length },
    { key: "documents", label: "Documents", count: data.documents.length },
    { key: "ordonnances", label: "Ordonnances", count: cd?.prescriptions?.length ?? 0 },
    { key: "cosium-paiements", label: "Paiements Cosium", count: cd?.cosium_payments?.length ?? 0 },
    { key: "rendez-vous", label: "Rendez-vous", count: cd?.calendar_events?.length ?? 0 },
    { key: "equipements", label: "Equipements", count: cd?.equipments?.length ?? 0 },
    ...(data.cosium_id ? [{ key: "cosium-docs" as Tab, label: "Docs Cosium" }] : []),
    { key: "marketing", label: "Marketing" },
    { key: "historique", label: "Historique", count: data.interactions.length },
  ];

  return (
    <PageLayout
      title={`${data.first_name} ${data.last_name}`}
      breadcrumb={[{ label: "Clients", href: "/clients" }, { label: `${data.first_name} ${data.last_name}` }]}
      actions={
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => downloadPdf(`/clients/${id}/360/pdf`, `client_${id}_360.pdf`)}
          >
            <Download className="h-4 w-4 mr-1" /> Fiche PDF
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              setShowForm(true);
              setActiveTab("historique");
            }}
          >
            <Plus className="h-4 w-4 mr-1" /> Note
          </Button>
          <Button variant="danger" onClick={() => setShowDelete(true)}>
            <Trash2 className="h-4 w-4 mr-1" /> Supprimer
          </Button>
        </div>
      }
    >
      {/* Avatar + identity header */}
      <AvatarUpload
        clientId={id}
        firstName={data.first_name}
        lastName={data.last_name}
        avatarUrl={data.avatar_url}
        email={data.email}
        phone={data.phone}
        onUploaded={() => mutate()}
      />

      {/* Cosium ID badge + correction actuelle + tags */}
      {(data.cosium_id || correction) && (
        <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
          {data.cosium_id && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 border border-blue-200">
              Cosium #{data.cosium_id}
            </span>
          )}
          {correction && (
            <span className="inline-flex items-center gap-2 text-text-secondary">
              <Eye className="h-4 w-4" aria-hidden="true" />
              <span className="font-medium text-text-primary">Correction :</span>
              OD {formatDiopter(correction.sphere_right)}
              {correction.cylinder_right !== null && ` (${formatDiopter(correction.cylinder_right)})`}
              {correction.addition_right !== null && ` Add ${formatDiopter(correction.addition_right)}`}
              {" | "}
              OG {formatDiopter(correction.sphere_left)}
              {correction.cylinder_left !== null && ` (${formatDiopter(correction.cylinder_left)})`}
              {correction.addition_left !== null && ` Add ${formatDiopter(correction.addition_left)}`}
            </span>
          )}
          {cd?.last_visit_date && (
            <span className="inline-flex items-center gap-1 text-text-secondary">
              <Calendar className="h-4 w-4" aria-hidden="true" />
              Derniere visite : {new Date(cd.last_visit_date).toLocaleDateString("fr-FR")}
            </span>
          )}
        </div>
      )}

      {/* Customer tags */}
      {cd?.customer_tags && cd.customer_tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-medium text-text-secondary">Tags :</span>
          {cd.customer_tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700 border border-purple-200"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <KPICard icon={Euro} label="CA Cosium" value={formatMoney(cd?.total_ca_cosium ?? 0)} color="primary" />
        <KPICard icon={Euro} label="Total facture" value={formatMoney(fin.total_facture)} color="primary" />
        <KPICard icon={CheckCircle} label="Total paye" value={formatMoney(fin.total_paye)} color="success" />
        <KPICard
          icon={Clock}
          label="Reste du"
          value={formatMoney(fin.reste_du)}
          color={fin.reste_du > 0 ? "danger" : "success"}
        />
        <KPICard icon={FolderOpen} label="Dossiers" value={data.dossiers.length} color="info" />
      </div>

      {/* Tabs navigation */}
      <div className="border-b border-border mb-6">
        <div className="flex gap-0 overflow-x-auto" role="tablist" aria-label="Sections du client">
          {tabs.map((t) => (
            <button
              key={t.key}
              role="tab"
              aria-selected={activeTab === t.key}
              aria-controls={`tabpanel-${t.key}`}
              id={`tab-${t.key}`}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:outline-none ${activeTab === t.key ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"}`}
            >
              {t.label}
              {t.count !== undefined && t.count > 0 && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Tab panels */}
      {activeTab === "resume" && (
        <TabResume
          firstName={data.first_name}
          lastName={data.last_name}
          phone={data.phone}
          email={data.email}
          socialSecurityNumber={data.social_security_number}
          postalCode={data.postal_code}
          city={data.city}
          renewalEligible={renewalEligible}
          renewalMonths={renewalMonths}
          interactions={data.interactions}
          correction={cd?.correction_actuelle ?? null}
          totalCaCosium={cd?.total_ca_cosium ?? 0}
          lastVisitDate={cd?.last_visit_date ?? null}
          nextRdv={cd?.calendar_events?.find((ev) => !ev.canceled && ev.start_date && new Date(ev.start_date) > new Date()) ?? null}
          cosiumInvoices={data.cosium_invoices}
        />
      )}
      {activeTab === "dossiers" && <TabDossiers dossiers={data.dossiers} />}
      {activeTab === "finances" && (
        <TabFinances
          devis={data.devis}
          factures={data.factures}
          paiements={data.paiements}
          cosiumInvoices={data.cosium_invoices}
        />
      )}
      {activeTab === "documents" && <TabDocuments documents={data.documents} />}
      {activeTab === "marketing" && <TabMarketing consentements={data.consentements} />}
      {activeTab === "cosium-docs" && <TabCosiumDocuments cosiumId={data.cosium_id} />}
      {activeTab === "ordonnances" && (
        <TabOrdonnances prescriptions={cd?.prescriptions ?? []} />
      )}
      {activeTab === "cosium-paiements" && (
        <TabCosiumPaiements payments={cd?.cosium_payments ?? []} />
      )}
      {activeTab === "rendez-vous" && (
        <TabRendezVous events={cd?.calendar_events ?? []} />
      )}
      {activeTab === "equipements" && (
        <TabEquipements equipments={cd?.equipments ?? []} />
      )}
      {activeTab === "historique" && (
        <TabHistorique
          interactions={data.interactions}
          showForm={showForm}
          onShowForm={setShowForm}
          intType={intType}
          onIntTypeChange={setIntType}
          intDir={intDir}
          onIntDirChange={setIntDir}
          intSubj={intSubj}
          onIntSubjChange={setIntSubj}
          intBody={intBody}
          onIntBodyChange={setIntBody}
          submitting={submitting}
          onSubmit={addInteraction}
        />
      )}

      <ConfirmDialog
        open={showDelete}
        title="Supprimer le client"
        message={`Etes-vous sur de vouloir supprimer ${data.first_name} ${data.last_name} ? Cette action est irreversible.`}
        confirmLabel={deleting ? "Suppression..." : "Supprimer"}
        danger
        onConfirm={handleDelete}
        onCancel={() => setShowDelete(false)}
      />
    </PageLayout>
  );
}
