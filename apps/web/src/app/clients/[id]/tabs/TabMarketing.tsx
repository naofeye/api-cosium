"use client";

interface Consentement {
  canal: string;
  consenti: boolean;
}

interface TabMarketingProps {
  consentements: Consentement[];
}

export function TabMarketing({ consentements }: TabMarketingProps) {
  return (
    <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
      <h3 className="text-lg font-semibold mb-4">Consentements marketing</h3>
      {consentements.length === 0 ? (
        <p className="text-sm text-text-secondary">Aucun consentement enregistre.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {consentements.map((c) => (
            <div
              key={c.canal}
              className={`flex items-center gap-3 rounded-lg px-4 py-3 ${c.consenti ? "bg-emerald-50 text-emerald-700" : "bg-gray-50 text-text-secondary"}`}
            >
              <div className={`h-3 w-3 rounded-full ${c.consenti ? "bg-emerald-500" : "bg-gray-300"}`} />
              <span className="text-sm font-medium capitalize">{c.canal}</span>
              <span className="ml-auto text-xs">{c.consenti ? "Actif" : "Inactif"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
