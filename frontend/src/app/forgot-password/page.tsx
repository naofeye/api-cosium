"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { FormField, FormInput } from "@/components/form/FormField";

const forgotSchema = z.object({
  email: z.string().min(1, "L'adresse email est obligatoire").email("Adresse email invalide"),
});

type ForgotFormData = z.infer<typeof forgotSchema>;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

export default function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<ForgotFormData>({
    resolver: zodResolver(forgotSchema),
    mode: "onChange",
  });

  const onSubmit = async (data: ForgotFormData) => {
    setServerError("");
    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: data.email }),
      });
      if (!res.ok && res.status !== 204) {
        throw new Error("Une erreur est survenue. Veuillez reessayer.");
      }
      setSubmitted(true);
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Une erreur est survenue.");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-border bg-bg-card p-8 shadow-lg">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-white text-xl font-bold">
              O
            </div>
            <h1 className="text-2xl font-bold text-text-primary">Mot de passe oublie</h1>
            <p className="mt-1 text-sm text-text-secondary">
              Entrez votre adresse email pour recevoir un lien de reinitialisation.
            </p>
          </div>

          {submitted ? (
            <div className="space-y-4">
              <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
                Si un compte existe avec cet email, un lien de reinitialisation a ete envoye. Verifiez votre boite de
                reception.
              </div>
              <div className="text-center">
                <Link href="/login" className="text-sm text-primary hover:underline">
                  Retour a la connexion
                </Link>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <FormField label="Adresse email" error={errors.email?.message}>
                <FormInput
                  type="email"
                  placeholder="votre@email.com"
                  autoComplete="email"
                  autoFocus
                  error={!!errors.email}
                  {...register("email")}
                />
              </FormField>

              {serverError && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {serverError}
                </div>
              )}

              <Button type="submit" disabled={!isValid} loading={isSubmitting} className="w-full">
                Envoyer le lien de reinitialisation
              </Button>

              <div className="text-center">
                <Link href="/login" className="text-sm text-primary hover:underline">
                  Retour a la connexion
                </Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
