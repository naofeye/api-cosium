"use client";

import { useEffect, useState, use as usePromise } from "react";
import { CheckCircle2, FileText, ShieldCheck } from "lucide-react";

import { API_BASE } from "@/lib/config";

interface PublicDevis {
  id: number;
  numero: string;
  status: string;
  montant_ht: number;
  tva: number;
  montant_ttc: number;
  part_secu: number;
  part_mutuelle: number;
  reste_a_charge: number;
  valid_until: string | null;
  created_at: string;
  is_signed: boolean;
}

interface PageProps {
  params: Promise<{ token: string }>;
}

const CONSENT_TEXT =
  "En cliquant sur ACCEPTER, je confirme avoir pris connaissance du devis " +
  "et l'accepte sans reserve. Cette acceptation a la meme valeur qu'une " +
  "signature manuscrite (signature electronique simple, reglement eIDAS " +
  "UE 910/2014).";

function formatMoney(amount: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
  }).format(amount);
}

function formatDate(iso: string | null): string {
  if (!iso) return "-";
  return new Date(iso).toLocaleDateString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export default function PublicSignPage({ params }: PageProps) {
  const { token } = usePromise(params);

  const [devis, setDevis] = useState<PublicDevis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signing, setSigning] = useState(false);
  const [signed, setSigned] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/public/v1/devis/${token}`, {
          cache: "no-store",
        });
        if (!res.ok) {
          if (res.status === 404) {
            setError("Lien de signature invalide ou expire.");
          } else {
            setError("Impossible de charger le devis. Reessayez plus tard.");
          }
          return;
        }
        const data = (await res.json()) as PublicDevis;
        if (cancelled) return;
        setDevis(data);
        setSigned(data.is_signed);
      } catch {
        if (!cancelled) setError("Erreur reseau. Verifiez votre connexion.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const handleSign = async () => {
    setSigning(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/public/v1/devis/${token}/sign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ consent_text: CONSENT_TEXT }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(
          (data.detail as string) ||
            (data?.error?.message as string) ||
            "La signature n'a pas pu etre enregistree.",
        );
        return;
      }
      setSigned(true);
    } catch {
      setError("Erreur reseau lors de la signature.");
    } finally {
      setSigning(false);
    }
  };

  if (loading) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="text-gray-500">Chargement du devis...</div>
      </main>
    );
  }

  if (error && !devis) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="max-w-md rounded-xl border border-red-200 bg-red-50 p-6 text-center">
          <p className="font-semibold text-red-900">{error}</p>
          <p className="mt-2 text-sm text-red-700">
            Contactez votre opticien pour obtenir un nouveau lien.
          </p>
        </div>
      </main>
    );
  }

  if (!devis) return null;

  if (signed) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-gray-50 px-6">
        <div className="max-w-md rounded-xl border border-emerald-200 bg-white p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto h-16 w-16 text-emerald-600" aria-hidden="true" />
          <h1 className="mt-4 text-2xl font-bold text-gray-900">
            Devis signe
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Merci ! Votre devis n&deg; {devis.numero} a ete signe avec succes.
            Votre opticien va prendre contact avec vous pour la suite.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gray-50 px-6 py-12">
      <div className="mx-auto max-w-2xl">
        <header className="mb-8 text-center">
          <FileText className="mx-auto h-10 w-10 text-blue-600" aria-hidden="true" />
          <h1 className="mt-3 text-2xl font-bold text-gray-900">
            Signature de votre devis
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Devis n&deg; {devis.numero} - cree le {formatDate(devis.created_at)}
          </p>
        </header>

        <section className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h2 className="mb-4 text-base font-semibold text-gray-800">
            Recapitulatif
          </h2>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Montant HT</span>
              <span className="font-medium tabular-nums">
                {formatMoney(devis.montant_ht)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">TVA</span>
              <span className="font-medium tabular-nums">
                {formatMoney(devis.tva)}
              </span>
            </div>
            <div className="flex justify-between border-t border-gray-100 pt-2">
              <span className="text-gray-900 font-medium">Montant TTC</span>
              <span className="font-bold tabular-nums text-gray-900">
                {formatMoney(devis.montant_ttc)}
              </span>
            </div>
            {devis.part_secu > 0 && (
              <div className="flex justify-between text-xs text-gray-500">
                <span>Part Securite Sociale (estimation)</span>
                <span className="tabular-nums">{formatMoney(devis.part_secu)}</span>
              </div>
            )}
            {devis.part_mutuelle > 0 && (
              <div className="flex justify-between text-xs text-gray-500">
                <span>Part Mutuelle (estimation)</span>
                <span className="tabular-nums">{formatMoney(devis.part_mutuelle)}</span>
              </div>
            )}
            {devis.reste_a_charge > 0 && (
              <div className="flex justify-between border-t border-gray-100 pt-2 text-sm">
                <span className="text-gray-700">Reste a charge estime</span>
                <span className="font-semibold tabular-nums text-amber-700">
                  {formatMoney(devis.reste_a_charge)}
                </span>
              </div>
            )}
          </div>
          {devis.valid_until && (
            <p className="mt-4 text-xs text-gray-500">
              Devis valable jusqu&apos;au {formatDate(devis.valid_until)}.
            </p>
          )}
        </section>

        <section className="mb-6 rounded-xl border border-blue-100 bg-blue-50 p-6">
          <div className="flex items-start gap-3">
            <ShieldCheck
              className="mt-0.5 shrink-0 text-blue-600"
              size={20}
              aria-hidden="true"
            />
            <div className="text-sm text-blue-900">
              <p className="font-semibold">Signature electronique securisee</p>
              <p className="mt-2">{CONSENT_TEXT}</p>
              <p className="mt-2 text-xs">
                Votre adresse IP et votre navigateur seront enregistres comme
                preuve juridique de l&apos;acceptation. Aucune donnee bancaire
                n&apos;est demandee a cette etape.
              </p>
            </div>
          </div>
        </section>

        {error && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={handleSign}
            disabled={signing}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-6 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {signing ? "Enregistrement..." : "ACCEPTER ET SIGNER"}
          </button>
        </div>
      </div>
    </main>
  );
}
