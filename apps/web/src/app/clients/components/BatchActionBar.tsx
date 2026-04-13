import { Download, Users } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface Props {
  count: number;
  onExport: () => void;
  onCreateSegment: () => void;
  onClear: () => void;
  creatingSegment: boolean;
}

export function BatchActionBar({ count, onExport, onCreateSegment, onClear, creatingSegment }: Props) {
  if (count === 0) return null;
  const plural = count > 1 ? "s" : "";

  return (
    <div className="mb-4 flex items-center gap-3 rounded-xl border border-blue-200 bg-blue-50 px-4 py-3">
      <span className="text-sm font-medium text-blue-800">
        {count} client{plural} selectionne{plural}
      </span>
      <div className="flex-1" />
      <Button variant="outline" onClick={onExport}>
        <Download className="h-4 w-4 mr-1" />
        Exporter la selection (CSV)
      </Button>
      <Button onClick={onCreateSegment} disabled={creatingSegment}>
        <Users className="h-4 w-4 mr-1" />
        {creatingSegment ? "Creation..." : "Creer un segment marketing"}
      </Button>
      <button
        onClick={onClear}
        className="text-sm text-blue-600 hover:text-blue-800 ml-2"
        aria-label="Tout deselectionner"
      >
        Tout deselectionner
      </button>
    </div>
  );
}
