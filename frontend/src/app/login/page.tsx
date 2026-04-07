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
import { Eye } from "lucide-react";

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
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden px-4">
      {/* Background gradient + subtle pattern */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-600 via-blue-500 to-indigo-700" />
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            "radial-gradient(circle at 1px 1px, white 1px, transparent 0)",
          backgroundSize: "40px 40px",
        }}
      />
      {/* Decorative circles */}
      <div className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-white/5 blur-3xl" />
      <div className="absolute -bottom-32 -left-32 h-96 w-96 rounded-full bg-white/5 blur-3xl" />

      <div className="relative z-10 w-full max-w-md">
        {/* Logo + Branding */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-20 w-20 items-center justify-center rounded-2xl bg-white shadow-xl">
            <Eye className="h-10 w-10 text-blue-600" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">OptiFlow AI</h1>
          <p className="mt-2 text-blue-100 text-sm">
            Plateforme de gestion intelligente pour opticiens
          </p>
        </div>

        {/* Login Card */}
        <div className="rounded-2xl border border-white/20 bg-white p-8 shadow-2xl">
          <div className="mb-6 text-center">
            <h2 className="text-xl font-semibold text-gray-900">Bienvenue sur OptiFlow</h2>
            <p className="mt-1 text-sm text-gray-500">Connectez-vous pour acceder a votre espace</p>
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
              <Link href="/forgot-password" className="text-sm text-blue-600 hover:text-blue-700 hover:underline">
                Mot de passe oublié ?
              </Link>
            </div>
          </form>
        </div>

        {/* Footer */}
        <div className="mt-6 text-center">
          <p className="text-xs text-blue-200">
            OptiFlow AI v0.1.0 — Connecte a Cosium
          </p>
          <p className="mt-1 text-xs text-blue-300/60">
            &copy; {new Date().getFullYear()} OptiFlow. Tous droits reserves.
          </p>
        </div>
      </div>
    </div>
  );
}
