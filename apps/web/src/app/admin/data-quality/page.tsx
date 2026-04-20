import { PageLayout } from "@/components/layout/PageLayout";
import { DataQualitySection } from "../components/DataQualitySection";

export default function DataQualityPage() {
  return (
    <PageLayout
      title="Qualite des donnees"
      description="Taux de liaison Cosium et extraction OCR par type d'entite"
      breadcrumb={[{ label: "Admin", href: "/admin" }, { label: "Qualite des donnees" }]}
    >
      <DataQualitySection />
    </PageLayout>
  );
}
