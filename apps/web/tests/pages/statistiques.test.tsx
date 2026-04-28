import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("next/dynamic", () => ({
  default: () => {
    return function DynamicComponent() {
      return <div data-testid="statistiques-charts">Charts</div>;
    };
  },
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

vi.mock("@/components/ui/SkeletonCard", () => ({
  SkeletonCard: () => <div data-testid="skeleton-card">Loading...</div>,
}));

vi.mock("@/lib/api", () => ({
  API_BASE: "http://localhost:8000",
}));

const mockData = {
  financial: {
    ca_total: 55000,
    montant_facture: 52000,
    montant_encaisse: 48000,
    reste_a_encaisser: 7000,
    taux_recouvrement: 87.3,
  },
  operational: {
    dossiers_en_cours: 15,
    dossiers_complets: 60,
    taux_completude: 82.5,
    pieces_manquantes: 2,
  },
  commercial: {
    devis_en_cours: 6,
    devis_signes: 20,
    taux_conversion: 70.0,
    panier_moyen: 420,
    ca_par_mois: [{ mois: "2026-03", ca: 18000 }],
  },
  cosium: null,
};

vi.mock("swr", () => ({
  default: (key: string) => {
    if (typeof key === "string" && key.startsWith("/analytics/dashboard")) {
      return { data: mockData, error: undefined, isLoading: false, isValidating: false, mutate: vi.fn() };
    }
    return { data: undefined, error: undefined, isLoading: false, isValidating: false, mutate: vi.fn() };
  },
}));

import StatistiquesPage from "@/app/statistiques/page";

describe("StatistiquesPage", () => {
  it("affiche le titre Statistiques", () => {
    render(<StatistiquesPage />);
    expect(screen.getByRole("heading", { name: "Statistiques", level: 1 })).toBeInTheDocument();
  });

  it("affiche les selecteurs de periode", () => {
    render(<StatistiquesPage />);
    expect(screen.getByText("7 jours")).toBeInTheDocument();
    expect(screen.getByText("30 jours")).toBeInTheDocument();
    expect(screen.getByText("90 jours")).toBeInTheDocument();
    expect(screen.getByText("1 an")).toBeInTheDocument();
  });

  it("affiche les KPIs financiers", () => {
    render(<StatistiquesPage />);
    expect(screen.getByText("CA Total")).toBeInTheDocument();
    expect(screen.getByText("Encaisse")).toBeInTheDocument();
    expect(screen.getByText("Reste a encaisser")).toBeInTheDocument();
    expect(screen.getByText("Taux recouvrement")).toBeInTheDocument();
  });

  it("affiche les KPIs operationnels et commerciaux", () => {
    render(<StatistiquesPage />);
    expect(screen.getByText("Dossiers en cours")).toBeInTheDocument();
    expect(screen.getByText("Completude")).toBeInTheDocument();
    expect(screen.getByText("Panier moyen")).toBeInTheDocument();
    expect(screen.getByText("Taux conversion")).toBeInTheDocument();
  });

  it("affiche les boutons d'export", () => {
    render(<StatistiquesPage />);
    expect(screen.getByRole("button", { name: /rapport mensuel/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /exporter en pdf/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /exporter la balance clients/i })).toBeInTheDocument();
  });
});
