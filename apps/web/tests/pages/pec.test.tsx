import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
}));

const pecData = [
  {
    id: 1,
    customer_name: "Alice Dupont",
    organization_name: "MGEN",
    status: "soumise",
    montant_demande: 300.0,
    montant_accorde: null,
    created_at: "2026-03-10",
  },
  {
    id: 2,
    customer_name: "Bob Martin",
    organization_name: "Malakoff",
    status: "acceptee",
    montant_demande: 500.0,
    montant_accorde: 450.0,
    created_at: "2026-03-15",
  },
];

vi.mock("swr", () => ({
  default: (key: string) => {
    if (typeof key === "string" && key.startsWith("/pec")) {
      return { data: pecData, error: undefined, isLoading: false, isValidating: false, mutate: vi.fn() };
    }
    // Return safe empty data for GlobalSearch and other SWR calls
    return { data: undefined, error: undefined, isLoading: false, isValidating: false, mutate: vi.fn() };
  },
}));

import PecPage from "@/app/pec/page";

describe("PecPage", () => {
  it("affiche le titre PEC / Tiers payant", () => {
    render(<PecPage />);
    expect(screen.getByRole("heading", { name: "PEC / Tiers payant", level: 1 })).toBeInTheDocument();
  });

  it("affiche les donnees dans le tableau", () => {
    render(<PecPage />);
    expect(screen.getByText("Alice Dupont")).toBeInTheDocument();
    expect(screen.getByText("MGEN")).toBeInTheDocument();
    expect(screen.getByText("Bob Martin")).toBeInTheDocument();
  });

  it("affiche les KPIs de statut", () => {
    render(<PecPage />);
    expect(screen.getByText("Soumises")).toBeInTheDocument();
    expect(screen.getAllByText("En attente").length).toBeGreaterThan(0);
    expect(screen.getByText("Acceptees")).toBeInTheDocument();
    expect(screen.getByText("Refusees")).toBeInTheDocument();
  });

  it("affiche un selecteur de filtre de statut", () => {
    render(<PecPage />);
    const select = screen.getByRole("combobox", { name: /filtrer par statut/i });
    expect(select).toBeInTheDocument();
  });
});
