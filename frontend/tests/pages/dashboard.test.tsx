import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/dashboard",
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

const mockDashboardData = {
  financial: {
    ca_total: 45000,
    montant_facture: 42000,
    montant_encaisse: 38000,
    reste_a_encaisser: 7000,
    taux_recouvrement: 84.4,
  },
  aging: { buckets: [], total: 7000 },
  payers: { payers: [] },
  operational: { dossiers_en_cours: 12, dossiers_complets: 45, taux_completude: 78.9, pieces_manquantes: 3 },
  commercial: {
    devis_en_cours: 8,
    devis_signes: 15,
    taux_conversion: 65.2,
    panier_moyen: 350,
    ca_par_mois: [{ mois: "2026-01", ca: 15000 }],
  },
  marketing: { campagnes_total: 5, campagnes_envoyees: 3, messages_envoyes: 120 },
};

vi.mock("swr", () => ({
  default: (key: string) => {
    if (typeof key === "string" && key.startsWith("/analytics/dashboard")) {
      return { data: mockDashboardData, error: undefined, isLoading: false, mutate: vi.fn() };
    }
    if (key === "/renewals/dashboard") {
      return { data: null, error: undefined, isLoading: false, mutate: vi.fn() };
    }
    return { data: undefined, error: undefined, isLoading: false, mutate: vi.fn() };
  },
}));

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div data-testid="chart-container">{children}</div>,
  BarChart: ({ children }: { children: React.ReactNode }) => <div data-testid="bar-chart">{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Bar: () => null,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Cell: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
}));

vi.mock("@/lib/tenant-context", () => ({
  useTenant: () => ({
    tenantId: 1,
    tenantName: "Test",
    availableTenants: [],
    isMultiTenant: false,
    switchTenant: vi.fn(),
  }),
}));

import DashboardPage from "@/app/dashboard/page";

describe("DashboardPage", () => {
  it("affiche les cartes KPI financieres", () => {
    render(<DashboardPage />);
    expect(screen.getByText("CA total")).toBeInTheDocument();
    expect(screen.getByText("Encaisse")).toBeInTheDocument();
    expect(screen.getByText("Impayes")).toBeInTheDocument();
    expect(screen.getByText("Taux recouvrement")).toBeInTheDocument();
  });

  it("affiche les boutons selecteurs de periode", () => {
    render(<DashboardPage />);
    expect(screen.getByText("Aujourd'hui")).toBeInTheDocument();
    expect(screen.getByText("7 jours")).toBeInTheDocument();
    expect(screen.getByText("30 jours")).toBeInTheDocument();
    expect(screen.getByText("90 jours")).toBeInTheDocument();
  });

  it("affiche la zone de graphiques", () => {
    const { container } = render(<DashboardPage />);
    const charts = container.querySelectorAll("[data-testid='chart-container']");
    expect(charts.length).toBeGreaterThan(0);
  });
});
