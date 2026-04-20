import { StatusBadge } from "@/components/ui/StatusBadge";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";
import type { Column } from "@/components/ui/DataTable";
import type { CosiumInvoice } from "@/lib/types";

export const TYPE_OPTIONS = [
  { value: "INVOICE", label: "Factures uniquement" },
  { value: "", label: "Tous les types" },
  { value: "QUOTE", label: "Devis" },
  { value: "CREDIT_NOTE", label: "Avoir" },
];

export const SETTLED_OPTIONS = [
  { value: "", label: "Tous les statuts" },
  { value: "true", label: "Solde" },
  { value: "false", label: "Impaye" },
];

export function typeLabel(type: string): string {
  switch (type) {
    case "INVOICE":
      return "Facture";
    case "QUOTE":
      return "Devis";
    case "CREDIT_NOTE":
      return "Avoir";
    default:
      return type;
  }
}

export function buildInvoiceColumns(
  onClientClick: (inv: CosiumInvoice) => void,
): Column<CosiumInvoice>[] {
  return [
    {
      key: "invoice_number",
      header: "Numero",
      sortable: true,
      render: (row) => <span className="font-mono font-medium">{row.invoice_number}</span>,
    },
    {
      key: "invoice_date",
      header: "Date",
      sortable: true,
      render: (row) =>
        row.invoice_date ? (
          <DateDisplay date={row.invoice_date} />
        ) : (
          <span className="text-text-secondary">-</span>
        ),
    },
    {
      key: "customer_name",
      header: "Client",
      sortable: true,
      render: (row) =>
        row.customer_id ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClientClick(row);
            }}
            className="text-blue-600 hover:text-blue-700 hover:underline font-medium text-left"
            title="Voir la fiche client"
          >
            {row.customer_name || "-"}
          </button>
        ) : (
          <span>{row.customer_name || "-"}</span>
        ),
    },
    {
      key: "type",
      header: "Type",
      render: (row) => (
        <StatusBadge
          status={row.type === "INVOICE" ? "facturee" : row.type === "QUOTE" ? "brouillon" : "annulee"}
          label={typeLabel(row.type)}
        />
      ),
    },
    {
      key: "total_ti",
      header: "Montant TTC",
      sortable: true,
      className: "text-right",
      render: (row) => <MoneyDisplay amount={row.total_ti} bold />,
    },
    {
      key: "outstanding_balance",
      header: "Solde restant",
      sortable: true,
      className: "text-right",
      render: (row) => (
        <MoneyDisplay
          amount={row.outstanding_balance}
          className={row.outstanding_balance > 0 ? "text-red-600" : "text-emerald-600"}
        />
      ),
    },
    {
      key: "settled",
      header: "Statut",
      render: (row) =>
        row.settled ? (
          <StatusBadge status="payee" label="Solde" />
        ) : (
          <StatusBadge status="impayee" label="Impaye" />
        ),
    },
  ];
}
