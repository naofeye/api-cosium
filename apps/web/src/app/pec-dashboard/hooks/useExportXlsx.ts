import { useState } from "react";
import { API_BASE } from "@/lib/api";

export function useExportXlsx(statusFilter: string) {
  const [exporting, setExporting] = useState(false);

  const exportXlsx = async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      const resp = await fetch(`${API_BASE}/pec-preparations/export?${params.toString()}`, {
        credentials: "include",
      });
      if (!resp.ok) throw new Error("Erreur lors de l'export");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `pec_preparations_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      // Silent fail : l'utilisateur peut reessayer (bouton se reactive)
    } finally {
      setExporting(false);
    }
  };

  return { exporting, exportXlsx };
}
