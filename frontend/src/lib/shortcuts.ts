export function initShortcuts(): () => void {
  const handler = (e: KeyboardEvent) => {
    // Ignore shortcuts when typing in an input/textarea (except Escape)
    const tag = (e.target as HTMLElement)?.tagName;
    const isInput = tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT"
      || (e.target as HTMLElement)?.isContentEditable;

    // Escape = close any open modal (dispatch custom event)
    if (e.key === "Escape") {
      document.dispatchEvent(new CustomEvent("optiflow:close-modal"));
      return;
    }

    // Don't trigger shortcuts in inputs
    if (isInput) return;

    // ? = toggle keyboard shortcuts help
    if (e.key === "?" && !e.ctrlKey && !e.metaKey && !e.shiftKey) {
      e.preventDefault();
      document.dispatchEvent(new CustomEvent("optiflow:toggle-shortcuts-help"));
      return;
    }

    // Ctrl+K or Cmd+K = focus search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      const search = document.querySelector<HTMLInputElement>('[placeholder*="Rechercher"], [role="combobox"]');
      search?.focus();
      return;
    }

    // Ctrl+N or Cmd+N = new client
    if ((e.ctrlKey || e.metaKey) && e.key === "n" && !e.shiftKey) {
      e.preventDefault();
      window.location.href = "/clients?action=new";
      return;
    }

    // Ctrl+D or Cmd+D = dashboard
    if ((e.ctrlKey || e.metaKey) && e.key === "d" && !e.shiftKey) {
      e.preventDefault();
      window.location.href = "/dashboard";
      return;
    }

    // Ctrl+Shift+S = statistiques
    if ((e.ctrlKey || e.metaKey) && e.key === "S" && e.shiftKey) {
      e.preventDefault();
      window.location.href = "/statistiques";
      return;
    }
  };

  document.addEventListener("keydown", handler);
  return () => document.removeEventListener("keydown", handler);
}
