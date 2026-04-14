"use client";

import { useState } from "react";
import useSWR from "swr";
import { PageLayout } from "@/components/layout/PageLayout";
import { LoadingState } from "@/components/ui/LoadingState";
import { ErrorState } from "@/components/ui/ErrorState";
import { fetchJson } from "@/lib/api";
import { Send, Users, Megaphone } from "lucide-react";
import { SegmentPanel } from "./components/SegmentPanel";
import type { Segment } from "./components/SegmentPanel";
import { CampaignPanel } from "./components/CampaignPanel";
import type { Campaign } from "./components/CampaignPanel";
import { DynamicSegmentsPanel } from "./components/DynamicSegments";

interface CampaignStats {
  campaign_id: number;
  total_sent: number;
  total_failed: number;
}

type Tab = "segments" | "campaigns";

export default function MarketingPage() {
  const {
    data: segments,
    error: segErr,
    isLoading: segLoading,
    mutate: mutateSegments,
  } = useSWR<Segment[]>("/marketing/segments");
  const {
    data: campaigns,
    error: campErr,
    isLoading: campLoading,
    mutate: mutateCampaigns,
  } = useSWR<Campaign[]>("/marketing/campaigns");
  const [activeTab, setActiveTab] = useState<Tab>("campaigns");
  const [showSegForm, setShowSegForm] = useState(false);
  const [showCampForm, setShowCampForm] = useState(false);
  const [segName, setSegName] = useState("");
  const [segDesc, setSegDesc] = useState("");
  const [segHasEmail, setSegHasEmail] = useState(true);
  const [segCity, setSegCity] = useState("");
  const [campName, setCampName] = useState("");
  const [campSegId, setCampSegId] = useState<number | "">("");
  const [campSubject, setCampSubject] = useState("");
  const [campTemplate, setCampTemplate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sendResult, setSendResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isLoading = segLoading || campLoading;
  const fetchError = segErr?.message ?? campErr?.message ?? null;
  const mutateAll = () => {
    mutateSegments();
    mutateCampaigns();
  };
  const safeSegments = segments ?? [];
  const safeCampaigns = campaigns ?? [];

  const createSegment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    const rules: Record<string, unknown> = {};
    if (segHasEmail) rules.has_email = true;
    if (segCity.trim()) rules.city = segCity.trim();
    if (Object.keys(rules).length === 0) {
      setError("Le segment doit avoir au moins un filtre (email, ville, etc.)");
      return;
    }
    setSubmitting(true);
    try {
      await fetchJson("/marketing/segments", {
        method: "POST",
        body: JSON.stringify({ name: segName, description: segDesc || null, rules_json: rules }),
      });
      setShowSegForm(false);
      setSegName("");
      setSegDesc("");
      mutateSegments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setSubmitting(false);
    }
  };

  const createCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);
    try {
      await fetchJson("/marketing/campaigns", {
        method: "POST",
        body: JSON.stringify({
          name: campName,
          segment_id: campSegId,
          channel: "email",
          subject: campSubject,
          template: campTemplate,
        }),
      });
      setShowCampForm(false);
      setCampName("");
      setCampSubject("");
      setCampTemplate("");
      mutateCampaigns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    } finally {
      setSubmitting(false);
    }
  };

  const sendCampaign = async (campId: number) => {
    setSendResult(null);
    try {
      const stats = await fetchJson<CampaignStats>(`/marketing/campaigns/${campId}/send`, { method: "POST" });
      setSendResult(`Campagne envoyee : ${stats.total_sent} email(s), ${stats.total_failed} echec(s)`);
      mutateCampaigns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur");
    }
  };

  const displayError = fetchError ?? error;

  if (isLoading)
    return (
      <PageLayout title="Chargement..." breadcrumb={[{ label: "Marketing" }]}>
        <LoadingState text="Chargement du marketing..." />
      </PageLayout>
    );
  if (displayError)
    return (
      <PageLayout title="Erreur" breadcrumb={[{ label: "Marketing" }]}>
        <ErrorState
          message={displayError}
          onRetry={() => {
            setError(null);
            mutateAll();
          }}
        />
      </PageLayout>
    );

  return (
    <PageLayout
      title="Marketing"
      description="Segments, campagnes et consentements"
      breadcrumb={[{ label: "Marketing" }]}
    >
      {sendResult && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 flex items-center gap-2">
          <Send className="h-4 w-4" aria-hidden="true" /> {sendResult}
        </div>
      )}

      <DynamicSegmentsPanel />

      <div className="border-b border-border mb-6">
        <div className="flex gap-0">
          {[
            { key: "campaigns" as const, label: `Campagnes (${safeCampaigns.length})`, icon: Megaphone },
            { key: "segments" as const, label: `Segments (${safeSegments.length})`, icon: Users },
          ].map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              <tab.icon className="h-4 w-4" aria-hidden="true" /> {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "campaigns" && (
        <CampaignPanel
          campaigns={safeCampaigns}
          segments={safeSegments}
          showForm={showCampForm}
          onToggleForm={() => setShowCampForm(!showCampForm)}
          campName={campName}
          onCampNameChange={setCampName}
          campSegId={campSegId}
          onCampSegIdChange={setCampSegId}
          campSubject={campSubject}
          onCampSubjectChange={setCampSubject}
          campTemplate={campTemplate}
          onCampTemplateChange={setCampTemplate}
          submitting={submitting}
          onSubmit={createCampaign}
          onSend={sendCampaign}
        />
      )}

      {activeTab === "segments" && (
        <SegmentPanel
          segments={safeSegments}
          showForm={showSegForm}
          onToggleForm={() => setShowSegForm(!showSegForm)}
          segName={segName}
          onSegNameChange={setSegName}
          segDesc={segDesc}
          onSegDescChange={setSegDesc}
          segHasEmail={segHasEmail}
          onSegHasEmailChange={setSegHasEmail}
          segCity={segCity}
          onSegCityChange={setSegCity}
          submitting={submitting}
          onSubmit={createSegment}
        />
      )}
    </PageLayout>
  );
}
