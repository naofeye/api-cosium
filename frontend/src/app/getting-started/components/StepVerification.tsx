"use client";

import useSWR from "swr";
import { Button } from "@/components/ui/Button";
import { ArrowRight, Users, FileText, FolderOpen } from "lucide-react";

interface MetricsData {
  totals: {
    users: number;
    clients: number;
    dossiers: number;
    factures: number;
    paiements: number;
  };
}

export function StepVerification({ onNext }: { onNext: () => void }) {
  const { data: metrics } = useSWR<MetricsData>("/admin/metrics");

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">
          Verification des donnees
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Voici un apercu des donnees disponibles dans votre espace.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-gray-200 bg-white p-5 text-center">
          <Users className="mx-auto h-8 w-8 text-blue-500 mb-2" />
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.totals?.clients ?? 0}
          </p>
          <p className="text-sm text-gray-500">Clients importes</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 text-center">
          <FileText className="mx-auto h-8 w-8 text-amber-500 mb-2" />
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.totals?.factures ?? 0}
          </p>
          <p className="text-sm text-gray-500">Factures</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 text-center">
          <FolderOpen className="mx-auto h-8 w-8 text-purple-500 mb-2" />
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.totals?.dossiers ?? 0}
          </p>
          <p className="text-sm text-gray-500">Dossiers</p>
        </div>
        <div className="rounded-xl border border-gray-200 bg-white p-5 text-center">
          <Users className="mx-auto h-8 w-8 text-emerald-500 mb-2" />
          <p className="text-3xl font-bold text-gray-900">
            {metrics?.totals?.users ?? 0}
          </p>
          <p className="text-sm text-gray-500">Utilisateurs</p>
        </div>
      </div>

      {(metrics?.totals?.clients ?? 0) === 0 && (
        <div className="rounded-lg border border-amber-100 bg-amber-50 p-4">
          <p className="text-sm text-amber-700">
            Aucune donnee importee pour le moment. Vous pourrez synchroniser vos
            donnees depuis Cosium a tout moment via la page Administration.
          </p>
        </div>
      )}

      <Button onClick={onNext} className="w-full">
        Continuer
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}
