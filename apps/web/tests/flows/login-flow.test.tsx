import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockPush = vi.fn();
const mockReplace = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, prefetch: vi.fn() }),
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

describe("Login Flow - E2E style", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLogin.mockResolvedValue({
      role: "admin",
      tenant_id: 1,
      tenant_name: "Test",
      available_tenants: [],
    });
  });

  it("renders login form with email and password fields", () => {
    render(<LoginPage />);
    expect(screen.getByPlaceholderText("admin@optiflow.local")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Votre mot de passe")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /se connecter/i })).toBeInTheDocument();
  });

  it("shows validation error when submitting with empty fields", () => {
    render(<LoginPage />);
    const submitBtn = screen.getByRole("button", { name: /se connecter/i });
    // Button should be disabled when fields are empty (form validation via zod)
    expect(submitBtn).toBeDisabled();
  });

  it("redirects on successful login", async () => {
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
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/actions");
    });
  });

  it("shows error message when login fails", async () => {
    mockLogin.mockRejectedValue(new Error("Email ou mot de passe incorrect"));
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByPlaceholderText("admin@optiflow.local"), "wrong@test.com");
    await user.type(screen.getByPlaceholderText("Votre mot de passe"), "badpassword");

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /se connecter/i })).not.toBeDisabled();
    });

    await user.click(screen.getByRole("button", { name: /se connecter/i }));

    await waitFor(() => {
      expect(screen.getByText("Email ou mot de passe incorrect")).toBeInTheDocument();
    });
  });

  it("has a forgot password link that navigates correctly", () => {
    render(<LoginPage />);
    const forgotLink = screen.getByText("Mot de passe oublié ?");
    expect(forgotLink).toBeInTheDocument();
    expect(forgotLink.closest("a")).toHaveAttribute("href", "/forgot-password");
  });
});
