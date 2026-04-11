import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("swr", () => ({
  default: vi.fn(() => ({ data: null, error: undefined, isLoading: false, mutate: vi.fn() })),
}));

vi.mock("@/lib/auth", () => ({
  logout: vi.fn(),
  isAuthenticated: () => true,
  getTenantId: () => 1,
  getTenantName: () => "Test",
  getAvailableTenants: () => [],
}));

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn(),
}));

import { Header } from "@/components/layout/Header";

describe("DarkMode toggle", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark");
    localStorage.clear();
  });

  it("affiche le bouton de toggle mode sombre", () => {
    render(<Header />);
    const btn = screen.getByLabelText("Passer en mode sombre");
    expect(btn).toBeInTheDocument();
  });

  it("clic sur le bouton ajoute la classe dark", async () => {
    const user = userEvent.setup();
    render(<Header />);
    const btn = screen.getByLabelText("Passer en mode sombre");
    await user.click(btn);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });
});
