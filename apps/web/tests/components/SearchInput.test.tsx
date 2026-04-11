import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SearchInput } from "@/components/ui/SearchInput";

describe("SearchInput", () => {
  it("affiche le placeholder", () => {
    render(<SearchInput onSearch={vi.fn()} placeholder="Rechercher..." />);
    expect(screen.getByPlaceholderText("Rechercher...")).toBeInTheDocument();
  });

  it("accepte la saisie de texte", async () => {
    const user = userEvent.setup();
    render(<SearchInput onSearch={vi.fn()} />);
    const input = screen.getByRole("textbox");
    await user.type(input, "hello");
    expect(input).toHaveValue("hello");
  });

  it("affiche une icone de recherche", () => {
    const { container } = render(<SearchInput onSearch={vi.fn()} />);
    expect(container.querySelector("svg")).toBeTruthy();
  });
});
