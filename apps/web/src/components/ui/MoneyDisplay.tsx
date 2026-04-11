"use client";

import { cn } from "@/lib/utils";
import { formatMoney } from "@/lib/format";

interface MoneyDisplayProps {
  amount: number;
  className?: string;
  colored?: boolean;
  bold?: boolean;
}

export function MoneyDisplay({ amount, className, colored = false, bold = false }: MoneyDisplayProps) {
  const srLabel = colored
    ? amount > 0
      ? " (positif)"
      : amount < 0
        ? " (negatif)"
        : ""
    : "";

  return (
    <span
      className={cn(
        "tabular-nums",
        bold && "font-semibold",
        colored && amount > 0 && "text-success",
        colored && amount < 0 && "text-danger",
        className,
      )}
    >
      {formatMoney(amount)}
      {srLabel && <span className="sr-only">{srLabel}</span>}
    </span>
  );
}
