"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { PartyPopper } from "lucide-react";

export function StepComplete() {
  const router = useRouter();

  return (
    <div className="text-center py-4">
      <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
        <PartyPopper className="h-10 w-10 text-emerald-600" />
      </div>
      <h2 className="text-xl font-bold text-gray-900">Votre espace est pret !</h2>
      <p className="mt-2 text-sm text-gray-500 max-w-sm mx-auto">
        Felicitations ! Votre compte OptiFlow AI est configure. Vous pouvez maintenant acceder a votre tableau de bord.
      </p>
      <div className="mt-8 flex flex-col gap-3">
        <Button type="button" onClick={() => router.push("/actions")} className="w-full">
          Acceder a mon tableau de bord
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/getting-started")} className="w-full">
          Voir le guide de demarrage
        </Button>
      </div>
    </div>
  );
}
