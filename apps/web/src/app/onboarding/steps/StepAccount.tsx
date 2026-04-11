"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { fetchJson } from "@/lib/api";
import { Eye, EyeOff } from "lucide-react";
import { cn } from "@/lib/utils";
import { signupSchema, type SignupFormData } from "@/lib/schemas/onboarding";
import type { SignupResponse } from "../helpers";

export function StepAccount({ onComplete }: { onComplete: () => void }) {
  const { toast } = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isValid },
  } = useForm<SignupFormData>({
    resolver: zodResolver(signupSchema),
    mode: "onBlur",
    defaultValues: {
      company_name: "",
      owner_email: "",
      owner_password: "",
      owner_first_name: "",
      owner_last_name: "",
      phone: "",
    },
  });

  const onSubmit = async (data: SignupFormData) => {
    setApiError("");
    try {
      await fetchJson<SignupResponse>("/onboarding/signup", {
        method: "POST",
        credentials: "include",
        body: JSON.stringify({
          ...data,
          company_name: data.company_name.trim(),
          owner_email: data.owner_email.trim(),
          owner_first_name: data.owner_first_name.trim(),
          owner_last_name: data.owner_last_name.trim(),
          phone: data.phone?.trim() || undefined,
        }),
      });
      toast("Compte cree avec succes", "success");
      onComplete();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Impossible de creer le compte";
      setApiError(msg);
      toast(msg, "error");
    }
  };

  const inputClass = (fieldName: keyof SignupFormData) =>
    cn(
      "w-full rounded-lg border bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-100",
      errors[fieldName] ? "border-red-400 focus:border-red-500" : "border-gray-300 focus:border-blue-500",
    );

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <div className="text-center mb-6">
        <h2 className="text-xl font-bold text-gray-900">Creer votre compte</h2>
        <p className="mt-1 text-sm text-gray-500">
          Renseignez les informations de votre entreprise et votre compte administrateur.
        </p>
      </div>

      <div>
        <label htmlFor="company_name" className="mb-1.5 block text-sm font-medium text-gray-700">
          Nom de l&apos;entreprise *
        </label>
        <input
          id="company_name"
          type="text"
          {...register("company_name")}
          placeholder="Optique Dupont"
          className={inputClass("company_name")}
          autoFocus
        />
        {errors.company_name && <p className="mt-1 text-xs text-red-600">{errors.company_name.message}</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="owner_first_name" className="mb-1.5 block text-sm font-medium text-gray-700">
            Prenom *
          </label>
          <input
            id="owner_first_name"
            type="text"
            {...register("owner_first_name")}
            placeholder="Jean"
            className={inputClass("owner_first_name")}
          />
          {errors.owner_first_name && <p className="mt-1 text-xs text-red-600">{errors.owner_first_name.message}</p>}
        </div>
        <div>
          <label htmlFor="owner_last_name" className="mb-1.5 block text-sm font-medium text-gray-700">
            Nom *
          </label>
          <input
            id="owner_last_name"
            type="text"
            {...register("owner_last_name")}
            placeholder="Dupont"
            className={inputClass("owner_last_name")}
          />
          {errors.owner_last_name && <p className="mt-1 text-xs text-red-600">{errors.owner_last_name.message}</p>}
        </div>
      </div>

      <div>
        <label htmlFor="owner_email" className="mb-1.5 block text-sm font-medium text-gray-700">
          Adresse email *
        </label>
        <input
          id="owner_email"
          type="email"
          {...register("owner_email")}
          placeholder="jean.dupont@optique.fr"
          className={inputClass("owner_email")}
          autoComplete="email"
        />
        {errors.owner_email && <p className="mt-1 text-xs text-red-600">{errors.owner_email.message}</p>}
      </div>

      <div>
        <label htmlFor="owner_password" className="mb-1.5 block text-sm font-medium text-gray-700">
          Mot de passe *
        </label>
        <div className="relative">
          <input
            id="owner_password"
            type={showPassword ? "text" : "password"}
            {...register("owner_password")}
            placeholder="Minimum 8 caractères"
            className={cn(inputClass("owner_password"), "pr-10")}
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            aria-label={showPassword ? "Masquer le mot de passe" : "Afficher le mot de passe"}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {errors.owner_password && <p className="mt-1 text-xs text-red-600">{errors.owner_password.message}</p>}
      </div>

      <div>
        <label htmlFor="phone" className="mb-1.5 block text-sm font-medium text-gray-700">
          Telephone <span className="text-gray-400">(optionnel)</span>
        </label>
        <input
          id="phone"
          type="tel"
          {...register("phone")}
          placeholder="06 12 34 56 78"
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
      </div>

      {apiError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{apiError}</div>
      )}

      <Button type="submit" disabled={!isValid || isSubmitting} loading={isSubmitting} className="w-full">
        {isSubmitting ? "Creation en cours..." : "Creer mon compte"}
      </Button>
    </form>
  );
}
