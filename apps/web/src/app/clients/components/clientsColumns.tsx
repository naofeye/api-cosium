import Image from "next/image";
import type { Column } from "@/components/ui/DataTable";
import { DateDisplay } from "@/components/ui/DateDisplay";
import { API_BASE } from "@/lib/api";
import type { Customer } from "@/lib/types";

interface BuildArgs {
  selectedIds: Set<number>;
  totalSelectable: number;
  onToggleOne: (id: number) => void;
  onToggleAll: () => void;
}

function CompletenessCell({ score }: { score: number }) {
  const colorClass =
    score >= 75 ? "bg-emerald-500"
    : score >= 50 ? "bg-amber-500"
    : score >= 25 ? "bg-orange-500"
    : "bg-red-500";
  const textColor =
    score >= 75 ? "text-emerald-700"
    : score >= 50 ? "text-amber-700"
    : score >= 25 ? "text-orange-700"
    : "text-red-700";
  return (
    <div className="flex items-center gap-2" title={`Completude : ${score}%`}>
      <div className="w-16 h-2 rounded-full bg-gray-200 overflow-hidden">
        <div className={`h-full rounded-full ${colorClass} transition-all`} style={{ width: `${score}%` }} />
      </div>
      <span className={`text-xs font-medium ${textColor}`}>{score}%</span>
    </div>
  );
}

function NameCell({ row }: { row: Customer }) {
  return (
    <div className="flex items-center gap-2">
      {row.avatar_url ? (
        <Image
          src={`${API_BASE}/clients/${row.id}/avatar`}
          alt={`Photo de ${row.first_name} ${row.last_name}`}
          width={32}
          height={32}
          className="h-8 w-8 rounded-full object-cover"
          unoptimized
        />
      ) : (
        <div className="h-8 w-8 rounded-full bg-blue-100 flex items-center justify-center text-xs font-bold text-blue-700">
          {(row.first_name?.[0] || "").toUpperCase()}
          {(row.last_name?.[0] || "").toUpperCase()}
        </div>
      )}
      <span className="font-medium">{row.last_name} {row.first_name}</span>
    </div>
  );
}

export function buildClientsColumns({
  selectedIds,
  totalSelectable,
  onToggleOne,
  onToggleAll,
}: BuildArgs): Column<Customer>[] {
  const allChecked = selectedIds.size > 0 && selectedIds.size === totalSelectable;
  return [
    {
      key: "select",
      header: (
        <input
          type="checkbox"
          checked={allChecked}
          onChange={onToggleAll}
          aria-label="Tout selectionner"
        />
      ),
      render: (row) => (
        <input
          type="checkbox"
          checked={selectedIds.has(row.id)}
          onChange={(e) => { e.stopPropagation(); onToggleOne(row.id); }}
          onClick={(e) => e.stopPropagation()}
          aria-label={`Selectionner ${row.first_name} ${row.last_name}`}
        />
      ),
    },
    { key: "id", header: "ID", render: (row) => <span className="font-mono text-text-secondary">#{row.id}</span> },
    { key: "name", header: "Nom", render: (row) => <NameCell row={row} /> },
    { key: "phone", header: "Telephone", render: (row) => row.phone || "\u2014" },
    { key: "email", header: "Email", render: (row) => row.email || "\u2014" },
    { key: "city", header: "Ville", render: (row) => row.city || "\u2014" },
    {
      key: "completeness",
      header: "Completude",
      render: (row) => <CompletenessCell score={row.completeness?.score ?? 0} />,
    },
    { key: "date", header: "Cree le", render: (row) => <DateDisplay date={row.created_at} /> },
  ];
}
