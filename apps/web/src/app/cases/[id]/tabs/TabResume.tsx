import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { User, Phone, Mail, CheckCircle, AlertCircle, CircleDot } from "lucide-react";
import type { CaseDetail, CompletenessData } from "./types";

interface TabResumeProps {
  caseData: CaseDetail;
  completeness: CompletenessData | null;
}

export function TabResume({ caseData, completeness }: TabResumeProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Informations client</h3>
          <div className="space-y-3">
            <div className="flex items-center gap-3">
              <User className="h-4 w-4 text-text-secondary" />
              <span className="text-sm">{caseData.customer_name}</span>
            </div>
            <div className="flex items-center gap-3">
              <Phone className="h-4 w-4 text-text-secondary" />
              <span className="text-sm">{caseData.phone || "Non renseigne"}</span>
            </div>
            <div className="flex items-center gap-3">
              <Mail className="h-4 w-4 text-text-secondary" />
              <span className="text-sm">{caseData.email || "Non renseigne"}</span>
            </div>
          </div>
        </div>
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Informations dossier</h3>
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Statut</span>
              <StatusBadge status={caseData.status} />
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Source</span>
              <span>{caseData.source || "\u2014"}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-text-secondary">Date de creation</span>
              <DateDisplay date={caseData.created_at} />
            </div>
          </div>
        </div>
      </div>

      {completeness && (
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary">Completude du dossier</h3>
            {completeness.total_missing === 0 ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                <CheckCircle className="h-3.5 w-3.5" />
                Complet
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700">
                <AlertCircle className="h-3.5 w-3.5" />
                {completeness.total_missing} piece{completeness.total_missing > 1 ? "s" : ""} manquante
                {completeness.total_missing > 1 ? "s" : ""}
              </span>
            )}
          </div>
          <div className="mb-3">
            <div className="flex items-center justify-between text-xs text-text-secondary mb-1">
              <span>
                {completeness.total_present} / {completeness.total_required} pieces obligatoires
              </span>
              <span>
                {completeness.total_required > 0
                  ? Math.round((completeness.total_present / completeness.total_required) * 100)
                  : 100}
                %
              </span>
            </div>
            <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${completeness.total_missing === 0 ? "bg-emerald-500" : "bg-amber-500"}`}
                style={{
                  width: `${completeness.total_required > 0 ? (completeness.total_present / completeness.total_required) * 100 : 100}%`,
                }}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {completeness.items.map((item) => (
              <div
                key={item.code}
                className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm ${
                  item.present
                    ? "bg-emerald-50 text-emerald-700"
                    : item.is_required
                      ? "bg-red-50 text-red-700"
                      : "bg-gray-50 text-text-secondary"
                }`}
              >
                {item.present ? (
                  <CheckCircle className="h-4 w-4 shrink-0" />
                ) : (
                  <CircleDot className="h-4 w-4 shrink-0" />
                )}
                <span>{item.label}</span>
                {item.is_required && !item.present && <span className="ml-auto text-xs font-medium">Requis</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
