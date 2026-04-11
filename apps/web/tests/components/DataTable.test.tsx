import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DataTable, type Column } from "@/components/ui/DataTable";

interface TestRow {
  id: number;
  name: string;
  value: number;
}

const columns: Column<TestRow>[] = [
  { key: "id", header: "ID", render: (row) => <span>{row.id}</span> },
  { key: "name", header: "Nom", render: (row) => <span>{row.name}</span> },
  { key: "value", header: "Valeur", render: (row) => <span>{row.value}</span> },
];

const sampleData: TestRow[] = [
  { id: 1, name: "Alice", value: 100 },
  { id: 2, name: "Bob", value: 200 },
  { id: 3, name: "Claire", value: 300 },
];

describe("DataTable", () => {
  it("affiche les en-tetes de colonnes", () => {
    render(<DataTable columns={columns} data={sampleData} />);
    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Nom")).toBeInTheDocument();
    expect(screen.getByText("Valeur")).toBeInTheDocument();
  });

  it("affiche les donnees des lignes", () => {
    render(<DataTable columns={columns} data={sampleData} />);
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
  });

  it("affiche le LoadingState quand loading=true", () => {
    render(<DataTable columns={columns} data={[]} loading={true} />);
    expect(screen.getByText(/Chargement/)).toBeInTheDocument();
  });

  it("affiche l'ErrorState quand error est fourni", () => {
    const onRetry = vi.fn();
    render(<DataTable columns={columns} data={[]} error="Erreur serveur" onRetry={onRetry} />);
    expect(screen.getByText(/Erreur serveur/i)).toBeInTheDocument();
  });

  it("affiche l'EmptyState quand data est vide", () => {
    render(
      <DataTable
        columns={columns}
        data={[]}
        emptyTitle="Aucun element"
        emptyDescription="Commencez par en creer un."
      />,
    );
    expect(screen.getByText("Aucun element")).toBeInTheDocument();
    expect(screen.getByText("Commencez par en creer un.")).toBeInTheDocument();
  });

  it("appelle onRowClick au clic sur une ligne", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<DataTable columns={columns} data={sampleData} onRowClick={onClick} />);
    await user.click(screen.getByText("Alice"));
    expect(onClick).toHaveBeenCalledWith(sampleData[0]);
  });

  it("affiche la pagination quand total est fourni", () => {
    render(
      <DataTable columns={columns} data={sampleData} page={1} pageSize={25} total={50} onPageChange={vi.fn()} />,
    );
    expect(screen.getByText(/Page 1 sur/)).toBeInTheDocument();
  });
});
