import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowLeft, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { PageLayout } from "@/components/layout/PageLayout";

interface Props {
  title: string;
  description: string;
  icon: LucideIcon;
  features: string[];
  releaseEstimate?: string;
  backHref?: string;
}

export function ComingSoon({
  title,
  description,
  icon: Icon,
  features,
  releaseEstimate,
  backHref = "/dashboard",
}: Props) {
  return (
    <PageLayout
      title={title}
      breadcrumb={[{ label: "Dashboard", href: "/dashboard" }, { label: title }]}
      actions={
        <Link href={backHref}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" aria-hidden="true" /> Retour
          </Button>
        </Link>
      }
    >
      <div className="max-w-2xl mx-auto py-12">
        <div className="text-center">
          <div className="inline-flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30 mb-6">
            <Icon className="h-10 w-10 text-white" aria-hidden="true" />
          </div>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1 text-xs font-semibold text-blue-700 mb-4">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            Bientot disponible
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">{title}</h1>
          <p className="text-gray-600 leading-relaxed">{description}</p>
          {releaseEstimate && (
            <p className="mt-3 text-sm text-gray-500">
              Sortie estimee : <span className="font-semibold text-gray-700">{releaseEstimate}</span>
            </p>
          )}
        </div>

        <div className="mt-12 rounded-xl border border-gray-200 bg-white shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">
            Ce que vous pourrez faire
          </h2>
          <ul className="space-y-3">
            {features.map((f) => (
              <li key={f} className="flex items-start gap-3 text-sm text-gray-700">
                <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-blue-500 shrink-0" aria-hidden="true" />
                <span>{f}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-6 rounded-xl border border-blue-200 bg-blue-50 p-5 text-center">
          <p className="text-sm text-blue-900">
            Vous voulez etre averti(e) du lancement ?
          </p>
          <a
            href="mailto:product@optiflow.ai?subject=Notify%20me%20%E2%80%94%20{title}"
            className="mt-2 inline-flex items-center gap-2 text-sm font-semibold text-blue-700 hover:text-blue-900 underline"
          >
            Ecrire a l&apos;equipe produit
          </a>
        </div>
      </div>
    </PageLayout>
  );
}
