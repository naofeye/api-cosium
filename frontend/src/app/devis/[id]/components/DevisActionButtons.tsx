import React from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Button } from "@/components/ui/Button";
import { downloadPdf } from "@/lib/download";
import {
  Download,
  Send,
  CheckCircle,
  XCircle,
  Receipt,
  Copy,
  Edit,
  Eye,
  ShieldCheck,
  Printer,
} from "lucide-react";
import type { DevisDetail } from "./DevisTimeline";

interface DevisActionButtonsProps {
  devis: DevisDetail;
  changing: boolean;
  generating: boolean;
  duplicating: boolean;
  onChangeStatus: (status: string) => void;
  onGenerateFacture: () => void;
  onDuplicate: () => void;
  onConfirmCancel: () => void;
  onConfirmRefuse: () => void;
}

export function DevisActionButtons({
  devis,
  changing,
  generating,
  duplicating,
  onChangeStatus,
  onGenerateFacture,
  onDuplicate,
  onConfirmCancel,
  onConfirmRefuse,
}: DevisActionButtonsProps) {
  const buttons: React.ReactNode[] = [];

  buttons.push(<StatusBadge key="badge" status={devis.status} />);

  buttons.push(
    <Button
      key="print"
      variant="outline"
      size="sm"
      onClick={() => window.print()}
      className="no-print"
      aria-label="Imprimer le devis"
    >
      <Printer className="h-4 w-4" /> Imprimer
    </Button>,
  );

  buttons.push(
    <Button
      key="pdf"
      variant="outline"
      size="sm"
      onClick={() => downloadPdf(`/devis/${devis.id}/pdf`, `devis_${devis.numero}.pdf`)}
      aria-label="Telecharger en PDF"
    >
      <Download className="h-4 w-4" /> PDF
    </Button>,
  );

  buttons.push(
    <Button key="dup" variant="outline" size="sm" onClick={onDuplicate} disabled={duplicating} aria-label="Dupliquer ce devis">
      <Copy className="h-4 w-4" /> {duplicating ? "Duplication..." : "Dupliquer"}
    </Button>,
  );

  switch (devis.status) {
    case "brouillon":
      buttons.push(
        <Link key="edit" href={`/devis/${devis.id}/edit`}>
          <Button variant="outline" size="sm">
            <Edit className="h-4 w-4" /> Modifier
          </Button>
        </Link>,
      );
      buttons.push(
        <Button key="send" onClick={() => onChangeStatus("envoye")} disabled={changing}>
          <Send className="h-4 w-4" /> {changing ? "Envoi..." : "Envoyer au client"}
        </Button>,
      );
      buttons.push(
        <Button key="cancel" variant="danger" size="sm" onClick={onConfirmCancel} disabled={changing}>
          Annuler
        </Button>,
      );
      break;

    case "envoye":
      buttons.push(
        <Button key="sign" onClick={() => onChangeStatus("signe")} disabled={changing}>
          <CheckCircle className="h-4 w-4" /> {changing ? "Mise a jour..." : "Marquer comme signe"}
        </Button>,
      );
      buttons.push(
        <Button key="refuse" variant="danger" size="sm" onClick={onConfirmRefuse} disabled={changing}>
          <XCircle className="h-4 w-4" /> Marquer comme refuse
        </Button>,
      );
      break;

    case "signe":
      buttons.push(
        <Button key="facture" onClick={onGenerateFacture} disabled={generating}>
          <Receipt className="h-4 w-4" /> {generating ? "Generation..." : "Generer la facture"}
        </Button>,
      );
      buttons.push(
        <Link key="pec" href={`/pec?case_id=${devis.case_id}`}>
          <Button variant="outline" size="sm">
            <ShieldCheck className="h-4 w-4" /> Preparer PEC
          </Button>
        </Link>,
      );
      break;

    case "facture":
      if (devis.facture_id) {
        buttons.push(
          <Link key="viewfact" href={`/factures/${devis.facture_id}`}>
            <Button variant="outline" size="sm">
              <Eye className="h-4 w-4" /> Voir la facture
            </Button>
          </Link>,
        );
      }
      break;
  }

  return <div className="flex items-center gap-2 flex-wrap">{buttons}</div>;
}
