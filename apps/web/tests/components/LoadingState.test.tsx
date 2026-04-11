import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LoadingState } from "@/components/ui/LoadingState";

describe("LoadingState", () => {
  it("affiche les barres d'animation skeleton", () => {
    const { container } = render(<LoadingState />);
    const pulseElements = container.querySelectorAll(".animate-pulse");
    expect(pulseElements.length).toBeGreaterThan(0);
  });

  it("affiche le texte de chargement", () => {
    render(<LoadingState text="Chargement des dossiers..." />);
    expect(screen.getByText("Chargement des dossiers...")).toBeInTheDocument();
  });
});
