"use client";

import { KPICard } from "@/components/ui/KPICard";
import { formatMoney, formatDate } from "@/lib/format";
import { Euro, CheckCircle, Clock, FolderOpen, Eye, Calendar, AlertTriangle } from "lucide-react";
import { AvatarUpload } from "./AvatarUpload";

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

  return (
    <>
      {/* Avatar + identity header */}
      <AvatarUpload
        clientId={clientId}
        firstName={firstName}
        lastName={lastName}
        avatarUrl={avatarUrl}
        email={email}
        phone={phone}
        onUploaded={onAvatarUploaded}
      />

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
