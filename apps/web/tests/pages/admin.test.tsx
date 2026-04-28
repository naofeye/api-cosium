import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/admin",
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/dynamic", () => ({
  default: (_importFn: () => Promise<unknown>, opts?: { loading?: () => React.ReactNode }) => {
    // Return a component that renders the loading fallback or nothing
    return function DynamicComponent() {
      return opts?.loading ? opts.loading() : null;
    };
  },
}));

vi.mock("@/lib/logger", () => ({
  logger: { error: vi.fn(), info: vi.fn(), warn: vi.fn(), debug: vi.fn() },
}));

// Mock all admin sub-components to avoid deep dependency trees
vi.mock("@/app/admin/components/HealthStatus", () => ({
  HealthStatus: () => <div data-testid="health-status">HealthStatus</div>,
}));
vi.mock("@/app/admin/components/CosiumConnection", () => ({
  CosiumConnection: () => <div data-testid="cosium-connection">CosiumConnection</div>,
}));
vi.mock("@/app/admin/components/CosiumCookies", () => ({
  CosiumCookies: () => <div data-testid="cosium-cookies">CosiumCookies</div>,
}));
vi.mock("@/app/admin/components/ManualSync", () => ({
  ManualSync: () => <div data-testid="manual-sync">ManualSync</div>,
}));
vi.mock("@/app/admin/components/RecentActivity", () => ({
  RecentActivity: () => <div data-testid="recent-activity">RecentActivity</div>,
}));
vi.mock("@/app/admin/components/DataQualitySection", () => ({
  DataQualitySection: () => <div data-testid="data-quality">DataQualitySection</div>,
}));
vi.mock("@/components/ui/SkeletonCard", () => ({
  SkeletonCard: () => <div data-testid="skeleton-card">Loading...</div>,
}));

const mockMetrics = {
  totals: { users: 3, clients: 120, dossiers: 85, factures: 210 },
  activity: { actions_last_hour: 12, active_users_last_hour: 2 },
};

vi.mock("swr", () => ({
  default: (key: string) => {
    if (key === "/admin/metrics") {
      return { data: mockMetrics, isLoading: false, error: undefined, mutate: vi.fn() };
    }
    if (key === "/admin/health") {
      return { data: { status: "ok", services: [] }, isLoading: false, error: undefined, mutate: vi.fn() };
    }
    if (key === "/sync/status") {
      return { data: { connected: true }, isLoading: false, error: undefined, mutate: vi.fn() };
    }
    return { data: undefined, isLoading: false, error: undefined, mutate: vi.fn() };
  },
}));

import AdminPage from "@/app/admin/page";

describe("AdminPage", () => {
  it("affiche le titre Administration", () => {
    render(<AdminPage />);
    expect(screen.getByRole("heading", { name: "Administration", level: 1 })).toBeInTheDocument();
  });

  it("affiche les KPIs de metriques", () => {
    render(<AdminPage />);
    expect(screen.getByText("Utilisateurs")).toBeInTheDocument();
    expect(screen.getByText("Clients")).toBeInTheDocument();
    expect(screen.getByText("Dossiers")).toBeInTheDocument();
    expect(screen.getByText("Factures")).toBeInTheDocument();
  });

  it("affiche les liens de navigation admin", () => {
    render(<AdminPage />);
    expect(screen.getByRole("link", { name: /gestion des utilisateurs/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /journal d'audit/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /clients supprimes/i })).toBeInTheDocument();
  });

  it("affiche les composants de monitoring", () => {
    render(<AdminPage />);
    expect(screen.getByTestId("health-status")).toBeInTheDocument();
    expect(screen.getByTestId("cosium-connection")).toBeInTheDocument();
    expect(screen.getByTestId("manual-sync")).toBeInTheDocument();
  });
});
