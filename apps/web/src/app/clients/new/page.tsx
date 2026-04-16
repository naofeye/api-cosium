"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { PageLayout } from "@/components/layout/PageLayout";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { FormField, FormInput } from "@/components/form/FormField";
import { fetchJson } from "@/lib/api";
import { clientCreateSchema, type ClientCreateFormData } from "@/lib/schemas/client";

export default function NewClientPage() {
  const router = useRouter();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<ClientCreateFormData>({
    resolver: zodResolver(clientCreateSchema),
    mode: "onChange",
  });

  const onSubmit = async (data: ClientCreateFormData) => {
    try {
      const payload: Record<string, string> = {};
      for (const [k, v] of Object.entries(data)) {
        if (typeof v === "string" && v.trim()) payload[k] = v.trim();
      }
      const created = await fetchJson<{ id: number }>("/clients", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      toast("Client cree avec succes", "success");
      router.push(`/clients/${created.id}`);
    } catch (err) {
      toast(err instanceof Error ? err.message : "Erreur lors de la creation", "error");
    }
  };

  return (
    <PageLayout
      title="Nouveau client"
      breadcrumb={[{ label: "Clients", href: "/clients" }, { label: "Nouveau client" }]}
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold text-text-primary mb-6">Identite</h2>
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
            <FormField label="N° Securite sociale">
              <FormInput placeholder="1 85 12 75 108 234 56" {...register("social_security_number")} />
            </FormField>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold text-text-primary mb-6">Adresse</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div className="md:col-span-2">
              <FormField label="Adresse">
                <FormInput placeholder="12 rue de la Paix" {...register("address")} />
              </FormField>
            </div>
            <FormField label="Code postal">
              <FormInput placeholder="75001" {...register("postal_code")} />
            </FormField>
            <FormField label="Ville">
              <FormInput placeholder="Paris" {...register("city")} />
            </FormField>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-bg-card p-6 shadow-sm mb-6">
          <h2 className="text-lg font-semibold text-text-primary mb-6">Notes</h2>
          <textarea
            {...register("notes")}
            placeholder="Informations complementaires sur le client..."
            rows={4}
            className="w-full rounded-lg border border-border px-4 py-2.5 text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-blue-100 resize-none"
          />
        </div>

        <div className="sticky bottom-20 lg:bottom-0 flex justify-end gap-3 rounded-xl border border-border bg-bg-card p-4 shadow-sm">
          <Button variant="outline" type="button" onClick={() => router.push("/clients")}>
            Annuler
          </Button>
          <Button type="submit" disabled={!isValid} loading={isSubmitting}>
            {isSubmitting ? "Creation en cours..." : "Creer le client"}
          </Button>
        </div>
      </form>
    </PageLayout>
  );
}
