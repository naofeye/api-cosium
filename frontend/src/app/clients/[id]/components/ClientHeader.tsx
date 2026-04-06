"use client";

import { KPICard } from "@/components/ui/KPICard";
import { formatMoney, formatDate } from "@/lib/format";
import { Euro, CheckCircle, Clock, FolderOpen, Eye, Calendar, AlertTriangle, FileDown, ShieldCheck, Printer } from "lucide-react";
import { AvatarUpload } from "./AvatarUpload";
import { CopyButton } from "@/components/ui/CopyButton";
import { useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

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

function formatDiopter(value: number | null): string {
  if (value === null || value === undefined) return "-";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

interface ClientMutuelleInfo {
  id: number;
  mutuelle_name: string;
  active: boolean;
  source: string;
  confidence: number;
}

interface ClientHeaderProps {
  clientId: string;
  firstName: string;
  lastName: string;
  avatarUrl: string | null;
  email: string | null;
  phone: string | null;
  cosiumId: string | number | null;
  correction: CorrectionActuelle | null;
  lastVisitDate: string | null;
  customerTags: string[];
  mutuelles: ClientMutuelleInfo[];
  resumeFinancier: {
    total_facture: number;
    total_paye: number;
    reste_du: number;
    taux_recouvrement: number;
  };
  totalCaCosium: number;
  dossiersCount: number;
  onAvatarUploaded: () => void;
}

export function ClientHeader({
  clientId,
  firstName,
  lastName,
  avatarUrl,
  email,
  phone,
  cosiumId,
  correction,
  lastVisitDate,
  customerTags,
  mutuelles,
  resumeFinancier: fin,
  totalCaCosium,
  dossiersCount,
  onAvatarUploaded,
}: ClientHeaderProps) {
  // Calculate prescription age in months
  const correctionAge: number | null = (() => {
    if (!correction?.prescription_date) return null;
    try {
      const prescDate = new Date(correction.prescription_date);
      if (isNaN(prescDate.getTime())) return null;
      const now = new Date();
      return (now.getFullYear() - prescDate.getFullYear()) * 12 + (now.getMonth() - prescDate.getMonth());
    } catch {
      return null;
    }
  })();

  const [pdfLoading, setPdfLoading] = useState(false);

  const handleDownloadPDF = async () => {
    setPdfLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/clients/${clientId}/export-pdf`, {
        credentials: "include",
      });
      if (!resp.ok) throw new Error("Erreur lors du telechargement");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `fiche_client_${clientId}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // silently fail — could add toast here
    } finally {
      setPdfLoading(false);
    }
  };

  return (
    <>
      {/* Avatar + identity header + PDF download */}
      <div className="flex items-start justify-between">
        <AvatarUpload
          clientId={clientId}
          firstName={firstName}
          lastName={lastName}
          avatarUrl={avatarUrl}
          email={email}
          phone={phone}
          onUploaded={onAvatarUploaded}
        />
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => window.print()}
            className="no-print inline-flex items-center gap-2 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors"
            title="Imprimer la fiche client"
            aria-label="Imprimer la fiche client"
          >
            <Printer className="h-4 w-4" aria-hidden="true" />
            Imprimer
          </button>
          <button
            onClick={handleDownloadPDF}
            disabled={pdfLoading}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-bg-card px-3 py-2 text-sm font-medium text-text-secondary hover:bg-gray-100 transition-colors disabled:opacity-50"
            title="Telecharger la fiche client en PDF"
            aria-label="Telecharger la fiche client en PDF"
          >
            <FileDown className="h-4 w-4" aria-hidden="true" />
            {pdfLoading ? "Export..." : "Telecharger PDF"}
          </button>
        </div>
      </div>

      {/* Prescription expiry alert */}
      {correctionAge !== null && correctionAge > 24 && (
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-800 mb-4">
          <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" />
          Ordonnance de plus de {Math.floor(correctionAge / 12)} an{Math.floor(correctionAge / 12) > 1 ? "s" : ""} — Renouvellement recommande
        </div>
      )}

      {/* Cosium ID badge + correction actuelle */}
      {(cosiumId || correction) && (
        <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
          {cosiumId && (
            <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700 border border-blue-200">
              Cosium #{cosiumId}
              <CopyButton text={String(cosiumId)} label="le N. Client Cosium" />
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
          {lastVisitDate && (
            <span className="inline-flex items-center gap-1 text-text-secondary">
              <Calendar className="h-4 w-4" aria-hidden="true" />
              Derniere visite : {formatDate(lastVisitDate)}
            </span>
          )}
        </div>
      )}

      {/* Customer tags */}
      {customerTags.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-medium text-text-secondary">Tags :</span>
          {customerTags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700 border border-purple-200"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Mutuelle badges */}
      {mutuelles.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <ShieldCheck className="h-4 w-4 text-emerald-600 shrink-0" aria-hidden="true" />
          <span className="text-xs font-medium text-text-secondary">Mutuelle :</span>
          {mutuelles.filter(m => m.active).map((m) => (
            <span
              key={m.id}
              className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200"
              title={`Source : ${m.source} | Confiance : ${Math.round(m.confidence * 100)}%`}
            >
              {m.mutuelle_name}
            </span>
          ))}
        </div>
      )}

      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <KPICard icon={Euro} label="CA Cosium" value={formatMoney(totalCaCosium)} color="primary" />
        <KPICard icon={Euro} label="Total facture" value={formatMoney(fin.total_facture)} color="primary" />
        <KPICard icon={CheckCircle} label="Total paye" value={formatMoney(fin.total_paye)} color="success" />
        <KPICard
          icon={Clock}
          label="Reste du"
          value={formatMoney(fin.reste_du)}
          color={fin.reste_du > 0 ? "danger" : "success"}
        />
        <KPICard icon={FolderOpen} label="Dossiers" value={dossiersCount} color="info" />
      </div>
    </>
  );
}
