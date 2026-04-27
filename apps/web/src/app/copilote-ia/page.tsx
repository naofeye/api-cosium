import { PageLayout } from "@/components/layout/PageLayout";
import { ChatInterface } from "./components/ChatInterface";

export default function CopiloteIAPage() {
  return (
    <PageLayout
      title="Copilote IA"
      description="Posez vos questions en langage naturel. Le copilote analyse vos données et répond en streaming."
      breadcrumb={[{ label: "Accueil", href: "/" }, { label: "Copilote IA" }]}
    >
      <ChatInterface />
    </PageLayout>
  );
}
