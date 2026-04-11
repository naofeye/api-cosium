"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import {
  Rocket,
  LayoutDashboard,
  Users,
  Calendar,
} from "lucide-react";

const STORAGE_KEY = "optiflow_getting_started_done";

export function StepCestParti() {
  const router = useRouter();

  const handleFinish = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    router.push("/actions");
  };

  return (
    <div className="text-center space-y-6">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-emerald-100">
        <Rocket className="h-10 w-10 text-emerald-600" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900">
        Votre espace est pret !
      </h2>
      <p className="text-sm text-gray-500 max-w-sm mx-auto">
        Vous pouvez maintenant explorer OptiFlow AI. Voici les pages principales
        pour commencer :
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-lg mx-auto">
        <Link
          href="/actions"
          className="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:bg-gray-50 transition-colors"
        >
          <LayoutDashboard className="h-6 w-6 text-blue-600" />
          <span className="text-sm font-medium text-gray-900">
            Tableau de bord
          </span>
        </Link>
        <Link
          href="/clients"
          className="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:bg-gray-50 transition-colors"
        >
          <Users className="h-6 w-6 text-emerald-600" />
          <span className="text-sm font-medium text-gray-900">Clients</span>
        </Link>
        <Link
          href="/agenda"
          className="flex flex-col items-center gap-2 rounded-xl border border-gray-200 bg-white p-4 hover:bg-gray-50 transition-colors"
        >
          <Calendar className="h-6 w-6 text-amber-600" />
          <span className="text-sm font-medium text-gray-900">Agenda</span>
        </Link>
      </div>

      <Button onClick={handleFinish} className="mx-auto">
        <Rocket className="h-4 w-4 mr-2" />
        Acceder a mon espace
      </Button>
    </div>
  );
}
