"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { login } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { FormField, FormInput } from "@/components/form/FormField";
import { loginSchema, type LoginFormData } from "@/lib/schemas/auth";

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: "onChange",
  });

  const onSubmit = async (data: LoginFormData) => {
    setServerError("");
    try {
      await login(data.email, data.password);
      router.push("/actions");
    } catch (err) {
      setServerError(err instanceof Error ? err.message : "Email ou mot de passe incorrect");
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
            <h1 className="text-2xl font-bold text-text-primary">OptiFlow AI</h1>
            <p className="mt-1 text-sm text-text-secondary">Connectez-vous pour acceder a votre espace</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <FormField label="Adresse email" error={errors.email?.message}>
              <FormInput
                type="email"
                placeholder="admin@optiflow.local"
                autoComplete="email"
                autoFocus
                error={!!errors.email}
                {...register("email")}
              />
            </FormField>

            <FormField label="Mot de passe" error={errors.password?.message}>
              <FormInput
                type="password"
                placeholder="Votre mot de passe"
                autoComplete="current-password"
                error={!!errors.password}
                {...register("password")}
              />
            </FormField>

            {serverError && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                {serverError}
              </div>
            )}

            <Button type="submit" disabled={!isValid} loading={isSubmitting} className="w-full">
              Se connecter
            </Button>

            <div className="text-center">
              <Link href="/forgot-password" className="text-sm text-primary hover:underline">
                Mot de passe oublie ?
              </Link>
            </div>
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-text-secondary">
          OptiFlow AI v0.1 — Plateforme metier pour opticiens
        </p>
      </div>
    </div>
  );
}
