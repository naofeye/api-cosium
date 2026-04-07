"use client";

import { useEffect, useState } from "react";
import { X, Keyboard } from "lucide-react";

export interface ShortcutDef {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  label: string;
  category: string;
}

export const SHORTCUTS: ShortcutDef[] = [
  { key: "k", ctrl: true, label: "Rechercher", category: "Navigation" },
  { key: "n", ctrl: true, label: "Nouveau client", category: "Actions" },
  { key: "d", ctrl: true, label: "Dashboard", category: "Navigation" },
  { key: "s", ctrl: true, shift: true, label: "Statistiques", category: "Navigation" },
  { key: "Escape", label: "Fermer la modale", category: "General" },
  { key: "?", label: "Aide raccourcis", category: "General" },
];

/**
 * Renders the keyboard shortcuts help dialog.
 * Listens for the custom event dispatched by initShortcuts() in lib/shortcuts.ts.
 */
export function KeyboardShortcutsHelp() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const toggle = () => setOpen((prev) => !prev);
    const close = () => setOpen(false);
    document.addEventListener("optiflow:toggle-shortcuts-help", toggle);
    document.addEventListener("optiflow:close-modal", close);
    return () => {
      document.removeEventListener("optiflow:toggle-shortcuts-help", toggle);
      document.removeEventListener("optiflow:close-modal", close);
    };
  }, []);

  if (!open) return null;

  return <ShortcutsHelpDialog onClose={() => setOpen(false)} />;
}

interface ShortcutsHelpDialogProps {
  onClose: () => void;
}

function ShortcutsHelpDialog({ onClose }: ShortcutsHelpDialogProps) {
  const categories = Array.from(new Set(SHORTCUTS.map((s) => s.category)));

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Raccourcis clavier"
    >
      <div className="w-full max-w-md rounded-xl border border-border bg-bg-card shadow-xl">
        <div className="flex items-center justify-between border-b border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Keyboard className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="text-lg font-semibold text-text-primary">Raccourcis clavier</h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Fermer"
            title="Fermer"
          >
            <X className="h-4 w-4 text-text-secondary" aria-hidden="true" />
          </button>
        </div>
        <div className="px-6 py-4 space-y-5 max-h-[60vh] overflow-y-auto">
          {categories.map((cat) => (
            <div key={cat}>
              <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide mb-2">
                {cat}
              </h3>
              <div className="space-y-2">
                {SHORTCUTS.filter((s) => s.category === cat).map((shortcut) => (
                  <div
                    key={shortcut.label}
                    className="flex items-center justify-between"
                  >
                    <span className="text-sm text-text-primary">{shortcut.label}</span>
                    <ShortcutBadge shortcut={shortcut} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="border-t border-border px-6 py-3">
          <p className="text-xs text-text-secondary text-center">
            Appuyez sur <kbd className="rounded bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 text-xs font-mono">?</kbd> pour afficher/masquer cette aide
          </p>
        </div>
      </div>
    </div>
  );
}

function ShortcutBadge({ shortcut }: { shortcut: ShortcutDef }) {
  const parts: string[] = [];
  if (shortcut.ctrl) parts.push("Ctrl");
  if (shortcut.shift) parts.push("Shift");
  if (shortcut.key === "Escape") {
    parts.push("Echap");
  } else if (shortcut.key === "?") {
    parts.push("?");
  } else {
    parts.push(shortcut.key.toUpperCase());
  }

  return (
    <div className="flex items-center gap-1">
      {parts.map((p, i) => (
        <span key={i}>
          {i > 0 && <span className="text-text-secondary mx-0.5">+</span>}
          <kbd className="inline-flex items-center justify-center rounded bg-gray-100 dark:bg-gray-700 px-2 py-0.5 text-xs font-mono text-text-primary min-w-[24px]">
            {p}
          </kbd>
        </span>
      ))}
    </div>
  );
}
