import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: vi.fn(), prefetch: vi.fn() }),
}));

const mockLogin = vi.fn();
vi.mock("@/lib/auth", () => ({
  login: (...args: unknown[]) => mockLogin(...args),
  isAuthenticated: () => false,
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

import LoginPage from "@/app/login/page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLogin.mockResolvedValue({ role: "admin", tenant_id: 1, tenant_name: "Test", available_tenants: [] });
  });

  it("affiche les champs email et mot de passe", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText("admin@optiflow.local")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Votre mot de passe")).toBeInTheDocument();
  });

  it("affiche le bouton Se connecter", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /se connecter/i })).toBeInTheDocument();
  });

  it("bouton desactive quand les champs sont vides", () => {
    render(<LoginPage />);
    expect(screen.getByRole("button", { name: /se connecter/i })).toBeDisabled();
  });

  it("affiche une erreur sur email invalide", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    const emailInput = screen.getByPlaceholderText("admin@optiflow.local");
    await user.type(emailInput, "invalid-email");
    await user.tab();
    await waitFor(() => {
      expect(screen.getByText("Adresse email invalide")).toBeInTheDocument();
    });
  });

  it("appelle login() sur soumission valide", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("admin@optiflow.local"), "admin@optiflow.local");
    await user.type(screen.getByPlaceholderText("Votre mot de passe"), "admin123");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /se connecter/i })).not.toBeDisabled();
    });
    await user.click(screen.getByRole("button", { name: /se connecter/i }));
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("admin@optiflow.local", "admin123");
    });
  });

  it("affiche un message d'erreur quand login echoue", async () => {
    mockLogin.mockRejectedValue(new Error("Email ou mot de passe incorrect"));
    const user = userEvent.setup();
    render(<LoginPage />);
    await user.type(screen.getByPlaceholderText("admin@optiflow.local"), "admin@optiflow.local");
    await user.type(screen.getByPlaceholderText("Votre mot de passe"), "wrongpass");
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /se connecter/i })).not.toBeDisabled();
    });
    await user.click(screen.getByRole("button", { name: /se connecter/i }));
    await waitFor(() => {
      expect(screen.getByText("Email ou mot de passe incorrect")).toBeInTheDocument();
    });
  });
});
