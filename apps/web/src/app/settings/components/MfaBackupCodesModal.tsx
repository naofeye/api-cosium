"use client";

import { Copy, KeyRound } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface MfaBackupCodesModalProps {
  codes: string[];
  onCopyAll: () => void;
  onDismiss: () => void;
}

export function MfaBackupCodesModal({ codes, onCopyAll, onDismiss }: MfaBackupCodesModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-amber-100">
            <KeyRound className="h-5 w-5 text-amber-700" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Codes de secours</h3>
            <p className="text-xs text-gray-500">Affiches une seule fois. Conservez-les en lieu sur.</p>
          </div>
        </div>
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 mb-4">
          <p className="text-xs text-amber-800 mb-3">
            Chaque code est utilisable une seule fois si vous perdez votre telephone.
            Stockez-les dans un gestionnaire de mots de passe ou imprimez-les.
          </p>
          <div className="grid grid-cols-2 gap-2 font-mono text-sm">
            {codes.map((code) => (
              <code key={code} className="rounded bg-white border border-amber-200 px-2 py-1 text-center">
                {code}
              </code>
            ))}
          </div>
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="outline" size="sm" onClick={onCopyAll}>
            <Copy className="h-4 w-4 mr-1" />
            Copier tout
          </Button>
          <Button size="sm" onClick={onDismiss}>
            J&apos;ai note mes codes
          </Button>
        </div>
      </div>
    </div>
  );
}
