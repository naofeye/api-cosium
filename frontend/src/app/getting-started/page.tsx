"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import useSWR from "swr";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { fetchJson } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import {
  Check,
  Sparkles,
  Link2,
  RefreshCw,
  Database,
  Rocket,
  ArrowLeft,
  ArrowRight,
  SkipForward,
  Users,
  FileText,
  ShoppingBag,
  CheckCircle,
  XCircle,
  LayoutDashboard,
  Calendar,
  FolderOpen,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const STORAGE_KEY = "optiflow_getting_started_done";

const STEP_DEFS = [
  { id: 1, label: "Bienvenue", icon: Sparkles },
  { id: 2, label: "Connexion Cosium", icon: Link2 },
  { id: 3, label: "Synchronisation", icon: RefreshCw },
  { id: 4, label: "Verification", icon: Database },
  { id: 5, label: "C'est parti !", icon: Rocket },
] as const;

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SyncStatus {
  configured: boolean;
  authenticated: boolean;
  tenant: string | null;
  tenant_name: string | null;
  base_url: string;
  last_sync_at: string | null;
  first_sync_done: boolean;
}

interface SyncCounts {
  customers: number;
  invoices: number;
  products: number;
}

interface MetricsData {
  totals: {
    users: number;
    clients: number;
    dossiers: number;
    factures: number;
    paiements: number;
  };
}

/* ------------------------------------------------------------------ */
/*  Progress Bar                                                       */
/* ------------------------------------------------------------------ */

function ProgressBar({ current, total }: { current: number; total: number }) {
  const pct = ((current - 1) / (total - 1)) * 100;
  return (
    <div className="w-full max-w-2xl mx-auto mb-8">
      <div className="flex items-center justify-between mb-2">
        {STEP_DEFS.map((step) => {
          const isCompleted = current > step.id;
          const isActive = current === step.id;
          const Icon = step.icon;
          return (
            <div key={step.id} className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-full text-sm font-semibold transition-colors",
                  isCompleted && "bg-emerald-600 text-white",
                  isActive && "bg-blue-600 text-white",
                  !isCompleted && !isActive && "bg-gray-200 text-gray-500"
                )}
              >
                {isCompleted ? (
                  <Check className="h-5 w-5" />
                ) : (
                  <Icon className="h-5 w-5" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs font-medium hidden sm:block",
                  isActive && "text-blue-600",
                  isCompleted && "text-emerald-600",
                  !isCompleted && !isActive && "text-gray-400"
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      <div className="relative h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="absolute inset-y-0 left-0 bg-blue-600 rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-center text-xs text-gray-500">
        Etape {current} sur {total}
      </p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 1 — Bienvenue                                                 */
/* ------------------------------------------------------------------ */

function StepBienvenue({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center space-y-6">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-blue-100">
        <Sparkles className="h-10 w-10 text-blue-600" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900">
        Bienvenue sur OptiFlow AI
      </h2>
      <div className="max-w-md mx-auto space-y-3 text-sm text-gray-600 text-left">
        <p>
          OptiFlow AI est votre plateforme metier tout-en-un pour la gestion de
          votre magasin d&apos;optique :
        </p>
        <ul className="space-y-2">
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>CRM client</strong> : fiches 360, historique, prescriptions
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Gestion documentaire</strong> : devis, factures,
              ordonnances
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Tiers payant</strong> : preparation PEC, suivi mutuelles
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Synchronisation Cosium</strong> : import automatique de vos
              donnees ERP
            </span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
            <span>
              <strong>Assistants IA</strong> : aide a la decision, relances
              intelligentes
            </span>
          </li>
        </ul>
        <p className="text-gray-500 pt-2">
          Ce guide va vous accompagner pour configurer votre espace en quelques
          minutes.
        </p>
      </div>
      <Button onClick={onNext} className="mx-auto">
        Commencer la configuration
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 2 — Connexion Cosium                                          */
/* ------------------------------------------------------------------ */

function StepConnexionCosium({ onNext }: { onNext: () => void }) {
  const { data: syncStatus } = useSWR<SyncStatus>("/sync/status");
  const isConnected = syncStatus?.authenticated === true;

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">
          Connecter votre Cosium
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          OptiFlow se synchronise avec votre ERP Cosium pour importer vos
          donnees automatiquement.
        </p>
      </div>

      <div className="rounded-xl border border-gray-200 bg-gray-50 p-6 space-y-4">
        <div className="flex items-center gap-3">
          {isConnected ? (
            <CheckCircle className="h-6 w-6 text-emerald-500 shrink-0" />
          ) : (
            <XCircle className="h-6 w-6 text-amber-500 shrink-0" />
          )}
          <div>
            <p className="font-medium text-gray-900">
              {isConnected
                ? "Cosium est connecte"
                : "Cosium n'est pas encore connecte"}
            </p>
            <p className="text-sm text-gray-500">
              {isConnected
                ? `Tenant : ${syncStatus?.tenant_name || syncStatus?.tenant || "Connecte"}`
                : "Rendez-vous dans l'administration pour configurer la connexion."}
            </p>
          </div>
        </div>

        {!isConnected && (
          <Link href="/admin">
            <Button variant="outline" className="w-full">
              <Link2 className="h-4 w-4 mr-2" />
              Configurer la connexion Cosium
            </Button>
          </Link>
        )}
      </div>

      <div className="rounded-lg border border-blue-100 bg-blue-50 p-4">
        <p className="text-sm text-blue-700">
          <strong>Astuce :</strong> Vous pouvez aussi configurer cela plus tard
          depuis la page Administration. Vos donnees seront importees lors de la
          premiere synchronisation.
        </p>
      </div>

      <Button onClick={onNext} className="w-full">
        Continuer
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 3 — Premiere synchronisation                                  */
/* ------------------------------------------------------------------ */

function StepSynchronisation({ onNext }: { onNext: () => void }) {
  const { data: syncStatus, mutate: mutateSyncStatus } =
    useSWR<SyncStatus>("/sync/status");
  const { toast } = useToast();
  const [syncing, setSyncing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [syncResult, setSyncResult] = useState<SyncCounts | null>(null);

  const isConnected = syncStatus?.authenticated === true;
  const alreadySynced = syncStatus?.first_sync_done === true;

  const handleSync = useCallback(async () => {
    setSyncing(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((p) => Math.min(p + Math.random() * 15, 90));
    }, 500);
    try {
      const data = await fetchJson<{ status: string; details: SyncCounts }>(
        "/onboarding/first-sync",
        { method: "POST" }
      );
      setProgress(100);
      setSyncResult(data.details);
      mutateSyncStatus();
      toast("Synchronisation terminee avec succes", "success");
    } catch (err) {
      toast(
        err instanceof Error
          ? err.message
          : "Erreur lors de la synchronisation",
        "error"
      );
    } finally {
      clearInterval(interval);
      setSyncing(false);
    }
  }, [mutateSyncStatus, toast]);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-xl font-bold text-gray-900">
          Premiere synchronisation
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Importez vos clients, factures et produits depuis Cosium.
        </p>
      </div>

      {!isConnected && !alreadySynced && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center">
          <p className="text-sm text-amber-700">
            La connexion Cosium n&apos;est pas encore configuree. Vous pourrez
            synchroniser vos donnees une fois la connexion etablie.
          </p>
        </div>
      )}

      {(isConnected || alreadySynced) && !syncResult && !syncing && (
        <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center">
          <RefreshCw className="mx-auto h-12 w-12 text-blue-400 mb-4" />
          <p className="text-sm text-gray-600 mb-6">
            {alreadySynced
              ? "Une synchronisation a deja ete effectuee. Vous pouvez en relancer une."
              : "Cliquez sur le bouton ci-dessous pour lancer l'importation."}
          </p>
          <Button onClick={handleSync}>Lancer la synchronisation</Button>
        </div>
      )}

      {syncing && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-8 text-center space-y-4">
          <div className="mx-auto mb-2 h-10 w-10 animate-spin rounded-full border-4 border-blue-200 border-t-blue-600" />
          <p className="text-sm font-medium text-blue-700">
            Synchronisation en cours...
          </p>
          <div className="w-full bg-blue-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-blue-600 h-full rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-blue-500">
            {Math.round(progress)}% — Veuillez patienter
          </p>
        </div>
      )}

      {syncResult && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle className="h-5 w-5 text-emerald-600" />
            <span className="text-sm font-semibold text-emerald-700">
              Synchronisation terminee
            </span>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <Users className="mx-auto h-6 w-6 text-blue-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.customers}
              </p>
              <p className="text-xs text-gray-500">Clients</p>
            </div>
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <FileText className="mx-auto h-6 w-6 text-amber-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.invoices}
              </p>
              <p className="text-xs text-gray-500">Factures</p>
            </div>
            <div className="rounded-lg bg-white p-4 text-center shadow-sm">
              <ShoppingBag className="mx-auto h-6 w-6 text-purple-500 mb-1" />
              <p className="text-2xl font-bold text-gray-900">
                {syncResult.products}
              </p>
              <p className="text-xs text-gray-500">Produits</p>
            </div>
          </div>
        </div>
      )}

      <Button onClick={onNext} className="w-full">
        Continuer
        <ArrowRight className="h-4 w-4 ml-2" />
      </Button>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 4 — Verification des donnees                                  */
/* ------------------------------------------------------------------ */

function StepVerification({ onNext }: { onNext: () => void }) {
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

/* ------------------------------------------------------------------ */
/*  Step 5 — C'est parti !                                             */
/* ------------------------------------------------------------------ */

function StepCestParti() {
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

/* ------------------------------------------------------------------ */
/*  Main Page                                                          */
/* ------------------------------------------------------------------ */

export default function GettingStartedPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(true);
  }, []);

  const goNext = () => setCurrentStep((prev) => Math.min(prev + 1, 5));
  const goPrev = () => setCurrentStep((prev) => Math.max(prev - 1, 1));

  const handleSkip = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    router.push("/actions");
  };

  if (!loaded) return null;

  return (
    <div className="flex min-h-screen flex-col items-center bg-gradient-to-br from-blue-50 via-white to-blue-50 px-4 py-8">
      <div className="mb-6 flex items-center gap-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white text-lg font-bold">
          O
        </div>
        <span className="text-xl font-bold text-gray-900">OptiFlow AI</span>
      </div>

      <ProgressBar current={currentStep} total={5} />

      <div className="w-full max-w-2xl rounded-2xl border border-gray-200 bg-white p-8 shadow-lg">
        {currentStep === 1 && <StepBienvenue onNext={goNext} />}
        {currentStep === 2 && <StepConnexionCosium onNext={goNext} />}
        {currentStep === 3 && <StepSynchronisation onNext={goNext} />}
        {currentStep === 4 && <StepVerification onNext={goNext} />}
        {currentStep === 5 && <StepCestParti />}
      </div>

      {/* Bottom navigation */}
      <div className="mt-6 flex items-center justify-between w-full max-w-2xl">
        <div>
          {currentStep > 1 && currentStep < 5 && (
            <button
              onClick={goPrev}
              className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Precedent
            </button>
          )}
        </div>
        <button
          onClick={handleSkip}
          className="inline-flex items-center gap-1 text-sm text-gray-400 hover:text-gray-600 transition-colors"
        >
          <SkipForward className="h-4 w-4" />
          Passer l&apos;introduction
        </button>
      </div>

      <p className="mt-6 text-center text-xs text-gray-400">
        OptiFlow AI — Plateforme metier pour opticiens
      </p>
    </div>
  );
}
