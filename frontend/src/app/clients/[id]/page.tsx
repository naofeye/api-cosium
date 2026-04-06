"use client";

import { useState, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { downloadPdf } from "@/lib/download";
import { Plus, Trash2, Download } from "lucide-react";
import Link from "next/link";

import { ClientHeader } from "./components/ClientHeader";
import { ClientTabs, type Tab } from "./components/ClientTabs";
import type { Client360 } from "./types";

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
    if (!data || !data.factures || data.factures.length === 0) return { renewalEligible: false, renewalMonths: 0 };
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
          action={<Link href="/clients"><Button>Retour a la liste</Button></Link>}
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

  const fin = data.resume_financier ?? { total_facture: 0, total_paye: 0, reste_du: 0, taux_recouvrement: 0 };
  const cd = data.cosium_data ?? null;

  return (
    <PageLayout
      title={`${data.first_name} ${data.last_name}`}
      breadcrumb={[{ label: "Clients", href: "/clients" }, { label: `${data.first_name} ${data.last_name}` }]}
      actions={
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => downloadPdf(`/clients/${id}/360/pdf`, `client_${id}_360.pdf`)}>
            <Download className="h-4 w-4 mr-1" /> Fiche PDF
          </Button>
          <Button variant="outline" onClick={() => { setShowForm(true); setActiveTab("historique"); }}>
            <Plus className="h-4 w-4 mr-1" /> Note
          </Button>
          <Button variant="danger" onClick={() => setShowDelete(true)}>
            <Trash2 className="h-4 w-4 mr-1" /> Supprimer
          </Button>
        </div>
      }
    >
      <ClientHeader
        clientId={id}
        firstName={data.first_name}
        lastName={data.last_name}
        avatarUrl={data.avatar_url}
        email={data.email}
        phone={data.phone}
        cosiumId={data.cosium_id}
        correction={cd?.correction_actuelle ?? null}
        lastVisitDate={cd?.last_visit_date ?? null}
        customerTags={cd?.customer_tags ?? []}
        mutuelles={cd?.mutuelles ?? []}
        resumeFinancier={fin}
        totalCaCosium={cd?.total_ca_cosium ?? 0}
        dossiersCount={data.dossiers.length}
        onAvatarUploaded={() => mutate()}
      />

      <ClientTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
        clientId={id}
        cosiumId={data.cosium_id}
        cosiumData={cd}
        dossiers={data.dossiers ?? []}
        devis={data.devis ?? []}
        factures={data.factures ?? []}
        paiements={data.paiements ?? []}
        documents={data.documents ?? []}
        consentements={data.consentements ?? []}
        interactions={data.interactions ?? []}
        cosiumInvoices={data.cosium_invoices ?? []}
        firstName={data.first_name}
        lastName={data.last_name}
        phone={data.phone}
        email={data.email}
        socialSecurityNumber={data.social_security_number}
        postalCode={data.postal_code}
        city={data.city}
        renewalEligible={renewalEligible}
        renewalMonths={renewalMonths}
        onDataRefresh={() => mutate()}
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
