import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ErrorState } from "@/components/ui/ErrorState";

describe("ErrorState", () => {
  it("affiche le message d'erreur", () => {
    render(<ErrorState message="Impossible de charger les donnees." />);
    expect(screen.getByText("Impossible de charger les donnees.")).toBeInTheDocument();
  });

  it("affiche le bouton Reessayer quand onRetry est fourni", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    render(<ErrorState message="Erreur" onRetry={onRetry} />);
    const btn = screen.getByRole("button", { name: /réessayer/i });
    expect(btn).toBeInTheDocument();
    await user.click(btn);
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("n'affiche pas le bouton Reessayer quand onRetry n'est pas fourni", () => {
    render(<ErrorState message="Erreur" />);
    expect(screen.queryByRole("button", { name: /réessayer/i })).not.toBeInTheDocument();
  });
});
