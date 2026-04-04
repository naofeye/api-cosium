export function initShortcuts(): () => void {
  const handler = (e: KeyboardEvent) => {
    // Ctrl+K or Cmd+K = focus search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      const search = document.querySelector<HTMLInputElement>('[placeholder*="Rechercher"]');
      search?.focus();
    }
  };

  document.addEventListener("keydown", handler);
  return () => document.removeEventListener("keydown", handler);
}
