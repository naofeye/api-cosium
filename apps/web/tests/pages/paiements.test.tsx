import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("swr", () => ({
  default: vi.fn(() => ({ data: undefined, error: undefined, isLoading: false, mutate: vi.fn() })),
  useSWRConfig: () => ({ mutate: vi.fn() }),
}));

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn().mockResolvedValue([]),
  API_BASE: "http://localhost:8000",
}));

vi.mock("@/lib/logger", () => ({
  logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

import PaiementsPage from "@/app/paiements/page";

describe("PaiementsPage", () => {
  it("affiche le titre Enregistrer un paiement", () => {
    render(<PaiementsPage />);
    expect(screen.getByRole("heading", { name: "Enregistrer un paiement", level: 1 })).toBeInTheDocument();
  });

  it("affiche les champs du formulaire", () => {
    render(<PaiementsPage />);
    expect(screen.getByText("Dossier *")).toBeInTheDocument();
    expect(screen.getByText("Type payeur *")).toBeInTheDocument();
    expect(screen.getByText("Mode de paiement")).toBeInTheDocument();
    expect(screen.getByText("Montant paye (EUR) *")).toBeInTheDocument();
  });

  it("affiche le bouton de soumission", () => {
    render(<PaiementsPage />);
    expect(screen.getByRole("button", { name: /enregistrer le paiement/i })).toBeInTheDocument();
  });

  it("affiche les options de type de payeur", () => {
    render(<PaiementsPage />);
    expect(screen.getByRole("option", { name: "Client" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Mutuelle" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Securite sociale" })).toBeInTheDocument();
  });

  it("affiche les options de mode de paiement", () => {
    render(<PaiementsPage />);
    expect(screen.getByRole("option", { name: "Carte bancaire" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Virement" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Cheque" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Especes" })).toBeInTheDocument();
  });
});
