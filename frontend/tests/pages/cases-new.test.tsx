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

vi.mock("@/lib/api", () => ({
  fetchJson: vi.fn(),
}));

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: vi.fn() }),
}));

import NewCasePage from "@/app/cases/new/page";

describe("NewCasePage", () => {
  it("affiche les champs nom et prenom", () => {
    render(<NewCasePage />);
    expect(screen.getByPlaceholderText("Dupont")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Jean")).toBeInTheDocument();
  });

  it("bouton desactive quand le nom est vide", () => {
    render(<NewCasePage />);
    const submitBtn = screen.getByRole("button", { name: /creer le dossier/i });
    expect(submitBtn).toBeDisabled();
  });

  it("affiche le select de source avec les options", () => {
    render(<NewCasePage />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Saisie manuelle" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Telephone" })).toBeInTheDocument();
  });

  it("affiche le titre Nouveau dossier", () => {
    render(<NewCasePage />);
    expect(screen.getByRole("heading", { name: "Nouveau dossier", level: 1 })).toBeInTheDocument();
  });
});
