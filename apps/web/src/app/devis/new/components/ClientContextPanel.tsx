import { Eye, ShieldCheck, Info } from "lucide-react";

export interface CorrectionData {
  sphere_right: number | null;
  cylinder_right: number | null;
  axis_right: number | null;
  addition_right: number | null;
  sphere_left: number | null;
  cylinder_left: number | null;
  axis_left: number | null;
  addition_left: number | null;
  prescription_date: string | null;
  prescriber_name: string | null;
}

export interface ClientMutuelleData {
  mutuelle_name: string;
  active: boolean;
}

export interface ClientContext {
  correction: CorrectionData | null;
  mutuelles: ClientMutuelleData[];
}

function formatDiopter(val: number | null): string {
  if (val === null || val === undefined) return "-";
  const sign = val >= 0 ? "+" : "";
  return `${sign}${val.toFixed(2)}`;
}

interface ClientContextPanelProps {
  clientContext: ClientContext | null;
  loadingContext: boolean;
}

export function ClientContextPanel({ clientContext, loadingContext }: ClientContextPanelProps) {
  if (loadingContext) {
    return (
      <div className="rounded-xl border border-border bg-bg-card p-4 shadow-sm mb-6 text-center text-sm text-text-secondary">
        Chargement des informations client...
      </div>
    );
  }

  if (!clientContext || (!clientContext.correction && clientContext.mutuelles.length === 0)) {
    return null;
  }

  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50/50 p-4 shadow-sm mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Info className="h-4 w-4 text-blue-600" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-blue-800">Informations client</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {clientContext.correction && (
          <div className="rounded-lg bg-white border border-blue-100 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <Eye className="h-3.5 w-3.5 text-blue-600" aria-hidden="true" />
              <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
                Correction actuelle
              </span>
              {clientContext.correction.prescription_date && (
                <span className="text-xs text-gray-500 ml-auto">
                  du {new Date(clientContext.correction.prescription_date).toLocaleDateString("fr-FR")}
                </span>
              )}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div>
                <span className="font-medium text-gray-600">OD :</span>{" "}
                <span className="text-gray-900 tabular-nums">
                  Sph {formatDiopter(clientContext.correction.sphere_right)}
                  {clientContext.correction.cylinder_right !== null && ` Cyl ${formatDiopter(clientContext.correction.cylinder_right)}`}
                  {clientContext.correction.axis_right !== null && ` Axe ${clientContext.correction.axis_right}\u00b0`}
                  {clientContext.correction.addition_right !== null && ` Add ${formatDiopter(clientContext.correction.addition_right)}`}
                </span>
              </div>
              <div>
                <span className="font-medium text-gray-600">OG :</span>{" "}
                <span className="text-gray-900 tabular-nums">
                  Sph {formatDiopter(clientContext.correction.sphere_left)}
                  {clientContext.correction.cylinder_left !== null && ` Cyl ${formatDiopter(clientContext.correction.cylinder_left)}`}
                  {clientContext.correction.axis_left !== null && ` Axe ${clientContext.correction.axis_left}\u00b0`}
                  {clientContext.correction.addition_left !== null && ` Add ${formatDiopter(clientContext.correction.addition_left)}`}
                </span>
              </div>
            </div>
            {clientContext.correction.prescriber_name && (
              <p className="text-xs text-gray-500 mt-1">
                Prescripteur : {clientContext.correction.prescriber_name}
              </p>
            )}
          </div>
        )}
        {clientContext.mutuelles.length > 0 && (
          <div className="rounded-lg bg-white border border-emerald-100 p-3">
            <div className="flex items-center gap-1.5 mb-2">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
              <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
                Mutuelle
              </span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {clientContext.mutuelles.map((m, i) => (
                <span
                  key={i}
                  className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 border border-emerald-200"
                >
                  {m.mutuelle_name}
                </span>
              ))}
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Renseignez la part mutuelle estimee dans les champs ci-dessus.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
