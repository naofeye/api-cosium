import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
}));

vi.mock("swr", () => ({
  default: vi.fn(() => ({ data: null, error: undefined, isLoading: false })),
}));

import { GlobalSearch } from "@/components/layout/GlobalSearch";

describe("GlobalSearch", () => {
  it("affiche le champ de recherche", () => {
    render(<GlobalSearch />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("affiche le placeholder", () => {
    render(<GlobalSearch />);
    expect(
      screen.getByPlaceholderText("Rechercher un client, dossier, devis, facture..."),
    ).toBeInTheDocument();
  });

  it("accepte la saisie de texte", async () => {
    const user = userEvent.setup();
    render(<GlobalSearch />);
    const input = screen.getByRole("textbox");
    await user.type(input, "Dupont");
    expect(input).toHaveValue("Dupont");
  });

  it("affiche le bouton effacer quand du texte est saisi", async () => {
    const user = userEvent.setup();
    render(<GlobalSearch />);
    const input = screen.getByRole("textbox");
    await user.type(input, "test");
    expect(screen.getByLabelText("Effacer")).toBeInTheDocument();
  });
});
