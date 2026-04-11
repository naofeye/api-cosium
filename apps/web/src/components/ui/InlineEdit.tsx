"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Pencil, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface InlineEditProps {
  value: string;
  onSave: (newValue: string) => Promise<void>;
  type?: "text" | "email" | "tel";
  placeholder?: string;
  className?: string;
  displayClassName?: string;
  emptyLabel?: string;
}

export function InlineEdit({
  value,
  onSave,
  type = "text",
  placeholder = "",
  className,
  displayClassName,
  emptyLabel = "Non renseigne",
}: InlineEditProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const blurTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup blur timer on unmount
  useEffect(() => {
    return () => {
      if (blurTimerRef.current) clearTimeout(blurTimerRef.current);
    };
  }, []);

  useEffect(() => {
    setDraft(value);
  }, [value]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const handleSave = useCallback(async () => {
    const trimmed = draft.trim();
    if (trimmed === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    try {
      await onSave(trimmed);
      setEditing(false);
    } catch {
      // Error handled by caller (toast)
    } finally {
      setSaving(false);
    }
  }, [draft, value, onSave]);

  const handleCancel = useCallback(() => {
    setDraft(value);
    setEditing(false);
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSave();
      } else if (e.key === "Escape") {
        e.preventDefault();
        handleCancel();
      }
    },
    [handleSave, handleCancel],
  );

  if (editing) {
    return (
      <span className={cn("inline-flex items-center gap-1", className)}>
        <input
          ref={inputRef}
          type={type}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => {
            // Small delay to allow click on check/cross buttons
            blurTimerRef.current = setTimeout(() => {
              blurTimerRef.current = null;
              if (editing && !saving) handleSave();
            }, 150);
          }}
          placeholder={placeholder}
          disabled={saving}
          className="rounded border border-primary bg-white px-2 py-0.5 text-sm outline-none focus:ring-1 focus:ring-primary min-w-[120px]"
        />
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleSave}
          disabled={saving}
          className="rounded p-0.5 text-emerald-600 hover:bg-emerald-50 transition-colors disabled:opacity-50"
          aria-label="Enregistrer"
          title="Enregistrer"
        >
          <Check className="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={handleCancel}
          disabled={saving}
          className="rounded p-0.5 text-red-500 hover:bg-red-50 transition-colors disabled:opacity-50"
          aria-label="Annuler"
          title="Annuler"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </span>
    );
  }

  return (
    <span
      role="button"
      tabIndex={0}
      onClick={() => setEditing(true)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setEditing(true);
        }
      }}
      className={cn(
        "group inline-flex items-center gap-1 cursor-pointer rounded px-1 -mx-1 hover:bg-gray-100 transition-colors",
        displayClassName,
      )}
      title="Cliquer pour modifier"
    >
      <span className={cn(!value && "italic text-text-secondary")}>
        {value || emptyLabel}
      </span>
      <Pencil className="h-3 w-3 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity shrink-0" aria-hidden="true" />
    </span>
  );
}
