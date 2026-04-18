import { formatDiopter } from "./types";

/**
 * Affiche les données structurées extraites par OCR. Rend un tableau OD/OG
 * spécialisé si les clés sphere_od/sphere_og (ou od_sphere/og_sphere) sont
 * présentes, sinon un rendu générique clé:valeur.
 */
export function StructuredDataDisplay({ data }: { data: string }) {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(data);
  } catch {
    return <pre className="text-xs text-text-secondary whitespace-pre-wrap">{data}</pre>;
  }

  // Check if it's an ordonnance with OD/OG data
  const hasODOG =
    parsed.sphere_od !== undefined ||
    parsed.sphere_og !== undefined ||
    parsed.od_sphere !== undefined ||
    parsed.og_sphere !== undefined;

  if (hasODOG) {
    const getVal = (key: string): string => {
      const v = parsed[key];
      if (v === null || v === undefined) return "-";
      return formatDiopter(v as number);
    };

    return (
      <div className="mt-2">
        <table className="text-xs border border-border rounded-lg overflow-hidden w-full max-w-md">
          <thead>
            <tr className="bg-gray-50 text-text-secondary">
              <th className="px-3 py-1.5 text-left font-medium"></th>
              <th className="px-3 py-1.5 text-center font-medium">Sphere</th>
              <th className="px-3 py-1.5 text-center font-medium">Cylindre</th>
              <th className="px-3 py-1.5 text-center font-medium">Axe</th>
              <th className="px-3 py-1.5 text-center font-medium">Addition</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-border">
              <td className="px-3 py-1.5 font-medium text-text-primary">OD</td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("sphere_od") !== "-" ? getVal("sphere_od") : getVal("od_sphere")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("cylinder_od") !== "-"
                  ? getVal("cylinder_od")
                  : getVal("od_cylinder")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("axis_od") !== "-" ? getVal("axis_od") : getVal("od_axis")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("addition_od") !== "-"
                  ? getVal("addition_od")
                  : getVal("od_addition")}
              </td>
            </tr>
            <tr className="border-t border-border">
              <td className="px-3 py-1.5 font-medium text-text-primary">OG</td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("sphere_og") !== "-" ? getVal("sphere_og") : getVal("og_sphere")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("cylinder_og") !== "-"
                  ? getVal("cylinder_og")
                  : getVal("og_cylinder")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("axis_og") !== "-" ? getVal("axis_og") : getVal("og_axis")}
              </td>
              <td className="px-3 py-1.5 text-center tabular-nums">
                {getVal("addition_og") !== "-"
                  ? getVal("addition_og")
                  : getVal("og_addition")}
              </td>
            </tr>
          </tbody>
        </table>
        {typeof parsed.prescriber_name === "string" && parsed.prescriber_name && (
          <p className="text-xs text-text-secondary mt-1">
            Prescripteur :{" "}
            <span className="font-medium">{parsed.prescriber_name}</span>
          </p>
        )}
        {typeof parsed.prescription_date === "string" && parsed.prescription_date && (
          <p className="text-xs text-text-secondary">Date : {parsed.prescription_date}</p>
        )}
      </div>
    );
  }

  // Generic structured data display
  const entries = Object.entries(parsed).filter(
    ([, v]) => v !== null && v !== undefined && v !== "",
  );
  if (entries.length === 0) return null;

  return (
    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
      {entries.map(([key, val]) => (
        <div key={key} className="flex gap-1">
          <span className="text-text-secondary">{key.replace(/_/g, " ")} :</span>
          <span className="font-medium text-text-primary">{String(val)}</span>
        </div>
      ))}
    </div>
  );
}
