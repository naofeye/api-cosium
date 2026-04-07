"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, SkipForward } from "lucide-react";
import { ProgressBar } from "./components/ProgressBar";
import { StepBienvenue } from "./components/StepBienvenue";
import { StepConnexionCosium } from "./components/StepConnexionCosium";
import { StepSynchronisation } from "./components/StepSynchronisation";
import { StepVerification } from "./components/StepVerification";
import { StepCestParti } from "./components/StepCestParti";

const STORAGE_KEY = "optiflow_getting_started_done";

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
