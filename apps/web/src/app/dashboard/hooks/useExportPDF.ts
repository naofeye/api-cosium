import { useCallback, useState } from "react";
import { API_BASE } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";

export function useExportPDF(dateFrom: string, dateTo: string) {
  const { toast } = useToast();
  const [exporting, setExporting] = useState(false);

  const exportPDF = useCallback(async () => {
    setExporting(true);
    try {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      const resp = await fetch(`${API_BASE}/exports/dashboard-pdf?${params.toString()}`, {
        credentials: "include",
      });
      if (!resp.ok) throw new Error("Erreur lors de l'export");
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dashboard_optiflow_${dateFrom || "all"}_${dateTo || "all"}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast("Impossible de telecharger le PDF. Reessayez.", "error");
    } finally {
      setExporting(false);
    }
  }, [dateFrom, dateTo, toast]);

  return { exporting, exportPDF };
}
