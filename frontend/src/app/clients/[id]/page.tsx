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
import { Euro, CheckCircle, Clock, FolderOpen, Plus, Trash2, Download } from "lucide-react";
import { downloadPdf } from "@/lib/download";

import { TabResume } from "./tabs/TabResume";
import { TabDossiers } from "./tabs/TabDossiers";
import { TabFinances } from "./tabs/TabFinances";
import { TabDocuments } from "./tabs/TabDocuments";
import { TabMarketing } from "./tabs/TabMarketing";
import { TabHistorique } from "./tabs/TabHistorique";

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
  resume_financier: { total_facture: number; total_paye: number; reste_du: number; taux_recouvrement: number };
}

type Tab = "resume" | "dossiers" | "finances" | "documents" | "marketing" | "historique";

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
  if (swrError || !data)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Clients", href: "/clients" }, { label: "Erreur" }]}>
        <ErrorState message={swrError?.message ?? "Client introuvable"} onRetry={() => mutate()} />
      </PageLayout>
    );

  const fin = data.resume_financier;
  const tabs: { key: Tab; label: string; count?: number }[] = [
    { key: "resume", label: "Resume" },
    { key: "dossiers", label: "Dossiers", count: data.dossiers.length },
    { key: "finances", label: "Finances", count: data.factures.length },
    { key: "documents", label: "Documents", count: data.documents.length },
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
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
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

      <div className="border-b border-border mb-6">
        <div className="flex gap-0 overflow-x-auto">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${activeTab === t.key ? "border-primary text-primary" : "border-transparent text-text-secondary hover:text-text-primary"}`}
            >
              {t.label}
              {t.count !== undefined && (
                <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs">{t.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>

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
        />
      )}
      {activeTab === "dossiers" && <TabDossiers dossiers={data.dossiers} />}
      {activeTab === "finances" && (
        <TabFinances devis={data.devis} factures={data.factures} paiements={data.paiements} />
      )}
      {activeTab === "documents" && <TabDocuments documents={data.documents} />}
      {activeTab === "marketing" && <TabMarketing consentements={data.consentements} />}
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
