import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/hooks/use-api", () => ({
  useFactures: () => ({
    data: [
      {
        id: 1,
        numero: "FA-2026-001",
        customer_name: "Jean Dupont",
        status: "payee",
        montant_ttc: 1250.5,
        date_emission: "2026-03-15",
      },
      {
        id: 2,
        numero: "FA-2026-002",
        customer_name: "Marie Martin",
        status: "impayee",
        montant_ttc: 890.0,
        date_emission: "2026-03-20",
      },
    ],
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

vi.mock("@/lib/export-csv", () => ({
  exportToCsv: vi.fn(),
}));

import FacturesPage from "@/app/factures/page";

describe("FacturesPage", () => {
  it("affiche le titre Factures", () => {
    render(<FacturesPage />);
    expect(screen.getByRole("heading", { name: "Factures", level: 1 })).toBeInTheDocument();
  });

  it("affiche les donnees dans le tableau", () => {
    render(<FacturesPage />);
    expect(screen.getByText("FA-2026-001")).toBeInTheDocument();
    expect(screen.getByText("Jean Dupont")).toBeInTheDocument();
    expect(screen.getByText("FA-2026-002")).toBeInTheDocument();
  });

  it("a un bouton Exporter CSV", () => {
    render(<FacturesPage />);
    expect(screen.getByText("Exporter CSV")).toBeInTheDocument();
  });
});
