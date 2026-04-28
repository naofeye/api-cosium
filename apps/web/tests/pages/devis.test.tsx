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
  useDevisList: () => ({
    data: [
      {
        id: 1,
        numero: "DV-2026-001",
        case_id: 10,
        status: "brouillon",
        montant_ttc: 450.0,
        reste_a_charge: 50.0,
        created_at: "2026-03-10",
      },
      {
        id: 2,
        numero: "DV-2026-002",
        case_id: 11,
        status: "signe",
        montant_ttc: 780.0,
        reste_a_charge: 0,
        created_at: "2026-03-20",
      },
    ],
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

import DevisListPage from "@/app/devis/page";

describe("DevisListPage", () => {
  it("affiche le titre Devis", () => {
    render(<DevisListPage />);
    expect(screen.getByRole("heading", { name: "Devis", level: 1 })).toBeInTheDocument();
  });

  it("affiche les donnees dans le tableau", () => {
    render(<DevisListPage />);
    expect(screen.getByText("DV-2026-001")).toBeInTheDocument();
    expect(screen.getByText("DV-2026-002")).toBeInTheDocument();
  });

  it("affiche un bouton Nouveau devis", () => {
    render(<DevisListPage />);
    expect(screen.getByRole("link", { name: "Nouveau devis" })).toBeInTheDocument();
  });

  it("affiche les onglets de filtres de statut", () => {
    render(<DevisListPage />);
    const tabs = screen.getAllByRole("tab");
    const tabNames = tabs.map((t) => t.textContent?.replace(/\d+/g, "").trim());
    expect(tabNames).toContain("Tous");
    expect(tabNames.some((n) => n?.includes("Brouillons"))).toBe(true);
    expect(tabNames.some((n) => n?.includes("Signes"))).toBe(true);
  });

  it("affiche les KPIs", () => {
    render(<DevisListPage />);
    expect(screen.getByText("Devis en cours")).toBeInTheDocument();
    expect(screen.getByText("Signes ce mois")).toBeInTheDocument();
    expect(screen.getByText("Taux de conversion")).toBeInTheDocument();
    expect(screen.getByText("Panier moyen")).toBeInTheDocument();
  });
});
