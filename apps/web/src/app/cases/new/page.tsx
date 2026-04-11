"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { FormField, FormInput } from "@/components/form/FormField";
import { fetchJson } from "@/lib/api";
import { caseCreateSchema, type CaseCreateFormData } from "@/lib/schemas/case";

export default function NewCasePage() {
  const router = useRouter();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<CaseCreateFormData>({
    resolver: zodResolver(caseCreateSchema),
    mode: "onChange",
    defaultValues: { source: "manual" },
  });

  const onSubmit = async (data: CaseCreateFormData) => {
    try {
      const created = await fetchJson<{ id: number }>("/cases", {
        method: "POST",
        body: JSON.stringify(data),
      });
      toast("Dossier cree avec succes", "success");
      router.push(`/cases/${created.id}`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la creation", "error");
    }
  };

  return (
    <PageLayout
      title="Nouveau dossier"
      breadcrumb={[{ label: "Dossiers", href: "/cases" }, { label: "Nouveau dossier" }]}
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-text-primary mb-6">Informations client</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <FormField label="Nom" required error={errors.last_name?.message}>
              <FormInput placeholder="Dupont" error={!!errors.last_name} {...register("last_name")} />
            </FormField>

            <FormField label="Prenom" required error={errors.first_name?.message}>
              <FormInput placeholder="Jean" error={!!errors.first_name} {...register("first_name")} />
            </FormField>

            <FormField label="Telephone">
              <FormInput type="tel" placeholder="06 12 34 56 78" {...register("phone")} />
            </FormField>

            <FormField label="Email" error={errors.email?.message}>
              <FormInput
                type="email"
                placeholder="jean.dupont@email.com"
                error={!!errors.email}
                {...register("email")}
              />
            </FormField>

            <FormField label="Source">
              <select
                {...register("source")}
                className="w-full rounded-lg border border-border bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-blue-100"
              >
                <option value="manual">Saisie manuelle</option>
                <option value="phone">Telephone</option>
                <option value="walk-in">Sans rendez-vous</option>
                <option value="web">Internet</option>
                <option value="referral">Recommandation</option>
              </select>
            </FormField>
          </div>
        </div>

        <div className="sticky bottom-0 mt-6 flex justify-end gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm">
          <Button variant="outline" type="button" onClick={() => router.push("/cases")}>
            Annuler
          </Button>
          <Button type="submit" disabled={!isValid} loading={isSubmitting}>
            {isSubmitting ? "Creation en cours..." : "Creer le dossier"}
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
