import { Tag } from "lucide-react";
import { cn } from "@/lib/utils";

interface VoucherCardProps {
  code: string;
  amount: number | string;
  expiresAt?: string | null;
  label?: string;
  className?: string;
}

/**
 * Carte bon d'achat : code, montant, expiration.
 * Code couleur : vert si > 30 jours, ambre < 30j, rouge < 7j ou expire.
 */
export function VoucherCard({ code, amount, expiresAt, label, className }: VoucherCardProps) {
  let remainingDays = Infinity;
  let expired = false;
  if (expiresAt) {
    const exp = new Date(expiresAt);
    if (!Number.isNaN(exp.getTime())) {
      remainingDays = Math.ceil((exp.getTime() - Date.now()) / (1000 * 60 * 60 * 24));
      expired = remainingDays < 0;
    }
  }

  const palette = expired
    ? "border-gray-300 bg-gray-50 text-gray-500"
    : remainingDays < 7
      ? "border-red-200 bg-red-50 text-red-900"
      : remainingDays < 30
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-emerald-200 bg-emerald-50 text-emerald-900";

  const amountStr =
    typeof amount === "number" ? amount.toLocaleString("fr-FR", { minimumFractionDigits: 2 }) : amount;

  return (
    <div
      className={cn(
        "flex items-center gap-3 rounded-xl border p-4 shadow-sm",
        palette,
        className,
      )}
      role="article"
      aria-label={`Bon d'achat ${code}`}
    >
      <div className="flex h-10 w-10 flex-none items-center justify-center rounded-lg bg-white/60">
        <Tag className="h-5 w-5" aria-hidden="true" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold truncate">{label ?? "Bon d'achat"}</p>
        <p className="font-mono text-xs opacity-80 truncate">{code}</p>
        {expiresAt && (
          <p className="text-xs mt-0.5 opacity-80">
            {expired ? "Expire" : remainingDays < 7 ? `Expire dans ${remainingDays}j` : `Valide ${remainingDays}j`}
          </p>
        )}
      </div>
      <div className="text-right flex-none">
        <p className="text-lg font-bold tabular-nums">{amountStr} EUR</p>
      </div>
    </div>
  );
}
