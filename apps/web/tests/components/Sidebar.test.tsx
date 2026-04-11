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

vi.mock("@/lib/sidebar-context", () => ({
  useSidebar: () => ({
    mobileOpen: false,
    openMobile: vi.fn(),
    closeMobile: vi.fn(),
    toggleMobile: vi.fn(),
  }),
}));

import { Sidebar } from "@/components/layout/Sidebar";

describe("Sidebar", () => {
  it("affiche les liens de navigation", () => {
    render(<Sidebar />);
    // Use getAllByText since labels appear in both desktop and mobile sidebars
    expect(screen.getAllByText("Dashboard").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Dossiers").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Clients").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Factures").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Paiements").length).toBeGreaterThanOrEqual(1);
  });

  it("affiche le lien Aide", () => {
    render(<Sidebar />);
    expect(screen.getAllByText("Aide").length).toBeGreaterThanOrEqual(1);
  });

  it("a un bouton pour reduire/agrandir la sidebar", async () => {
    const user = userEvent.setup();
    render(<Sidebar />);
    // The sidebar renders both desktop and mobile; find the collapse buttons
    const collapseBtns = screen.getAllByLabelText("Reduire le menu");
    expect(collapseBtns.length).toBeGreaterThanOrEqual(1);
    await user.click(collapseBtns[0]);
    expect(screen.getAllByLabelText("Agrandir le menu").length).toBeGreaterThanOrEqual(1);
  });
});
