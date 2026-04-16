import Link from "next/link";
import { FileDown, RefreshCw, Send } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface Props {
  clientId: string;
  refreshing: boolean;
  exporting: boolean;
  submitting: boolean;
  canSubmit: boolean;
  onRefresh: () => void;
  onExportPDF: () => void;
  onSubmit: () => void;
}

export function PecActionBar({
  clientId,
  refreshing,
  exporting,
  submitting,
  canSubmit,
  onRefresh,
  onExportPDF,
  onSubmit,
}: Props) {
  return (
    <div className="sticky bottom-20 lg:bottom-0 bg-white border-t border-gray-200 mt-6 p-4 flex justify-between items-center rounded-b-xl shadow-sm">
      <div className="flex gap-2">
        <Button variant="outline" onClick={onRefresh} loading={refreshing}>
          <RefreshCw className="h-4 w-4 mr-1" aria-hidden="true" /> Rafraichir
        </Button>
        <Button variant="outline" onClick={onExportPDF} loading={exporting}>
          <FileDown className="h-4 w-4 mr-1" aria-hidden="true" /> Exporter PDF
        </Button>
      </div>
      <div className="flex gap-2">
        <Link href={`/clients/${clientId}`}>
          <Button variant="ghost">Annuler</Button>
        </Link>
        <Button
          variant="primary"
          onClick={onSubmit}
          loading={submitting}
          disabled={!canSubmit}
          title={!canSubmit ? "Corrigez toutes les erreurs avant de soumettre" : "Soumettre la PEC"}
        >
          <Send className="h-4 w-4 mr-1" aria-hidden="true" /> Soumettre la PEC
        </Button>
      </div>
    </div>
  );
}
