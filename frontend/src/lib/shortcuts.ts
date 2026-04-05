export function initShortcuts(): () => void {
  const handler = (e: KeyboardEvent) => {
    // Ignore shortcuts when typing in an input/textarea
    const tag = (e.target as HTMLElement)?.tagName;
    const isInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT";

    // Ctrl+K or Cmd+K = focus search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      const search = document.querySelector<HTMLInputElement>('[placeholder*="Rechercher"]');
      search?.focus();
    }

    // Ctrl+N or Cmd+N = new dossier (only when not in an input)
    if ((e.ctrlKey || e.metaKey) && e.key === "n" && !isInput) {
      e.preventDefault();
      window.location.href = "/cases/new";
    }

    // Escape = close any open modal (dispatch custom event)
    if (e.key === "Escape") {
      document.dispatchEvent(new CustomEvent("optiflow:close-modal"));
    }
  };

  document.addEventListener("keydown", handler);
  return () => document.removeEventListener("keydown", handler);
}
