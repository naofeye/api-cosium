import { PageLayout } from "@/components/layout/PageLayout";
import { Building2 } from "lucide-react";

export default function AdminNetworkPage() {
  return (
    <PageLayout
      title="Administration Reseau"
      description="Gestion multi-magasins"
      breadcrumb={[{ label: "Admin", href: "/admin" }, { label: "Reseau" }]}
    >
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="mb-4 rounded-full bg-blue-50 p-4">
          <Building2 className="h-10 w-10 text-blue-500" aria-hidden="true" />
        </div>
        <h2 className="text-lg font-semibold text-text-primary mb-2">
          Bientot disponible
        </h2>
        <p className="text-sm text-text-secondary max-w-md">
          La gestion multi-magasins (administration reseau) sera disponible
          prochainement. Cette fonctionnalite vous permettra de gerer plusieurs
          points de vente depuis une interface centralisee.
        </p>
      </div>
    </PageLayout>
  );
}
