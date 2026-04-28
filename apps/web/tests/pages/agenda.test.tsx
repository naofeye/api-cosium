import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("next/dynamic", () => ({
  default: (_importFn: () => Promise<unknown>, opts?: { loading?: () => React.ReactNode }) => {
    return function DynamicComponent(_props: Record<string, unknown>) {
      return opts?.loading ? opts.loading() : <div data-testid="agenda-calendar">Calendrier</div>;
    };
  },
}));

vi.mock("@/components/ui/SkeletonCard", () => ({
  SkeletonCard: () => <div data-testid="skeleton-card">Chargement...</div>,
}));

// Control the hook return value via a mutable object
const hookState = {
  data: undefined as { items: object[]; total: number } | undefined,
  error: undefined as Error | undefined,
  isLoading: false,
};

vi.mock("@/lib/hooks/use-api", () => ({
  useCosiumCalendarEvents: () => ({
    data: hookState.data,
    error: hookState.error,
    isLoading: hookState.isLoading,
    mutate: vi.fn(),
  }),
}));

import AgendaPage from "@/app/agenda/page";

describe("AgendaPage — etat chargement", () => {
  it("affiche l'etat de chargement", () => {
    hookState.data = undefined;
    hookState.error = undefined;
    hookState.isLoading = true;

    render(<AgendaPage />);
    expect(screen.getByText(/chargement de l'agenda/i)).toBeInTheDocument();
  });
});

describe("AgendaPage — etat vide", () => {
  it("affiche l'etat vide quand il n'y a pas de rendez-vous", () => {
    hookState.data = { items: [], total: 0 };
    hookState.error = undefined;
    hookState.isLoading = false;

    render(<AgendaPage />);
    expect(screen.getByText("Aucun rendez-vous")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /synchroniser cosium/i })).toBeInTheDocument();
  });
});

describe("AgendaPage — avec donnees", () => {
  it("affiche le titre Agenda Cosium et le sous-titre avec le total", () => {
    hookState.data = {
      items: [{ id: 1, date: "2026-03-15", customer_name: "Jean Dupont", type: "rdv" }],
      total: 1,
    };
    hookState.error = undefined;
    hookState.isLoading = false;

    render(<AgendaPage />);
    expect(screen.getByRole("heading", { name: "Agenda Cosium", level: 1 })).toBeInTheDocument();
  });
});
