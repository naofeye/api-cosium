import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
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

import { Sidebar } from "@/components/layout/Sidebar";

describe("Sidebar", () => {
  it("affiche les liens de navigation", () => {
    render(<Sidebar />);
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Dossiers")).toBeInTheDocument();
    expect(screen.getByText("Clients")).toBeInTheDocument();
    expect(screen.getByText("Factures")).toBeInTheDocument();
    expect(screen.getByText("Paiements")).toBeInTheDocument();
  });

  it("affiche le lien Aide", () => {
    render(<Sidebar />);
    expect(screen.getByText("Aide")).toBeInTheDocument();
  });

  it("a un bouton pour reduire/agrandir la sidebar", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);
    const collapseBtn = screen.getByLabelText("Réduire le menu");
    expect(collapseBtn).toBeInTheDocument();
    await user.click(collapseBtn);
    expect(screen.getByLabelText("Agrandir le menu")).toBeInTheDocument();
  });
});
