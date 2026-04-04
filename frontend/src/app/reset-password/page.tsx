"use client";

import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/Button";
import { FormField, FormInput } from "@/components/form/FormField";

const resetSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "Le mot de passe doit contenir au moins 8 caracteres")
      .regex(/[A-Z]/, "Le mot de passe doit contenir au moins une majuscule")
      .regex(/\d/, "Le mot de passe doit contenir au moins un chiffre"),
    confirm_password: z.string().min(1, "Veuillez confirmer le mot de passe"),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    message: "Les mots de passe ne correspondent pas",
    path: ["confirm_password"],
  });

type ResetFormData = z.infer<typeof resetSchema>;

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [serverError, setServerError] = useState("");
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
    mode: "onChange",
  });

  if (!token) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          Lien de reinitialisation invalide. Veuillez demander un nouveau lien.
        </div>
        <div className="text-center">
          <Link href="/forgot-password" className="text-sm text-primary hover:underline">
            Demander un nouveau lien
          </Link>
        </div>
      </div>
    );
  }

  const onSubmit = async (data: ResetFormData) => {
    setServerError("");
    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ token, new_password: data.new_password }),
      });
      if (!res.ok && res.status !== 204) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.error?.message || body?.detail || "Le lien est invalide ou a expire.");
      }
      setSuccess(true);
      setTimeout(() => router.push("/login"), 3000);
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Une erreur est survenue.");
    }
  };

  if (success) {
    return (
      <div className="space-y-4">
        <div className="rounded-lg bg-emerald-50 border border-emerald-200 px-4 py-3 text-sm text-emerald-700">
          Mot de passe modifie avec succes. Vous allez etre redirige vers la page de connexion.
        </div>
        <div className="text-center">
          <Link href="/login" className="text-sm text-primary hover:underline">
            Aller a la connexion
          </Link>
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <FormField label="Nouveau mot de passe" error={errors.new_password?.message}>
        <FormInput
          type="password"
          placeholder="Minimum 8 caracteres, 1 majuscule, 1 chiffre"
          autoComplete="new-password"
          autoFocus
          error={!!errors.new_password}
          {...register("new_password")}
        />
      </FormField>

      <FormField label="Confirmer le mot de passe" error={errors.confirm_password?.message}>
        <FormInput
          type="password"
          placeholder="Repetez le mot de passe"
          autoComplete="new-password"
          error={!!errors.confirm_password}
          {...register("confirm_password")}
        />
      </FormField>

      {serverError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{serverError}</div>
      )}

      <Button type="submit" disabled={!isValid} loading={isSubmitting} className="w-full">
        Reinitialiser le mot de passe
      </Button>

      <div className="text-center">
        <Link href="/login" className="text-sm text-primary hover:underline">
          Retour a la connexion
        </Link>
      </div>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4">
      <div className="w-full max-w-md">
        <div className="rounded-2xl border border-border bg-bg-card p-8 shadow-lg">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-primary text-white text-xl font-bold">
              O
            </div>
            <h1 className="text-2xl font-bold text-text-primary">Nouveau mot de passe</h1>
            <p className="mt-1 text-sm text-text-secondary">Choisissez un nouveau mot de passe pour votre compte.</p>
          </div>
          <Suspense fallback={<div className="text-center text-sm text-text-secondary">Chargement...</div>}>
            <ResetPasswordForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
