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
  useClients: () => ({
    data: {
      items: [
        {
          id: 1,
          first_name: "Jean",
          last_name: "Dupont",
          phone: "0612345678",
          email: "jean@test.com",
          city: "Paris",
          created_at: "2026-01-01T00:00:00",
          avatar_url: null,
        },
      ],
      total: 1,
      page: 1,
      page_size: 25,
    },
    error: undefined,
    isLoading: false,
    mutate: vi.fn(),
  }),
}));

vi.mock("@/lib/export-csv", () => ({
  exportToCsv: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn(),
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import ClientsPage from "@/app/clients/page";

describe("ClientsPage", () => {
  it("affiche le titre Clients", () => {
    render(<ClientsPage />);
    expect(screen.getByRole("heading", { name: "Clients", level: 1 })).toBeInTheDocument();
  });

  it("affiche le nom du client dans le tableau", () => {
    render(<ClientsPage />);
    expect(screen.getByText(/Dupont/)).toBeInTheDocument();
    expect(screen.getByText(/Jean/)).toBeInTheDocument();
  });

  it("a un bouton Nouveau client", () => {
    render(<ClientsPage />);
    expect(screen.getByText("Nouveau client")).toBeInTheDocument();
  });

  it("a un bouton Importer", () => {
    render(<ClientsPage />);
    expect(screen.getByText("Importer")).toBeInTheDocument();
  });

  it("a un bouton Exporter CSV", () => {
    render(<ClientsPage />);
    expect(screen.getByText("Exporter CSV")).toBeInTheDocument();
  });
});
