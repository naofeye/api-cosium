"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { useToast } from "./Toast";

interface CopyButtonProps {
  text: string;
  label?: string;
  className?: string;
}

export function CopyButton({ text, label, className }: CopyButtonProps) {
  const { toast } = useToast();
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast("Copie !", "success");
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast("Impossible de copier dans le presse-papiers.", "error");
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={`Copier ${label || ""}`}
      aria-label={`Copier ${label || text}`}
      className={`inline-flex items-center justify-center rounded p-0.5 text-text-secondary hover:text-primary hover:bg-blue-50 transition-colors no-print ${className || ""}`}
    >
      {copied ? (
        <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
      ) : (
        <Copy className="h-3.5 w-3.5" aria-hidden="true" />
      )}
    </button>
  );
}
