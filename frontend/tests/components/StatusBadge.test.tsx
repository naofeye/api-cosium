import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "@/components/ui/StatusBadge";

describe("StatusBadge", () => {
  it("rend le label traduit pour brouillon", () => {
    render(<StatusBadge status="brouillon" />);
    expect(screen.getByText("Brouillon")).toBeInTheDocument();
  });

  it("applique la couleur verte pour complet", () => {
    render(<StatusBadge status="complet" />);
    const badge = screen.getByText("Complet");
    expect(badge.className).toContain("emerald");
  });

  it("applique la couleur rouge pour refuse", () => {
    render(<StatusBadge status="refuse" />);
    const badge = screen.getByText("Refuse");
    expect(badge.className).toContain("red");
  });

  it("applique la couleur bleue pour en_cours", () => {
    render(<StatusBadge status="en_cours" />);
    const badge = screen.getByText("En cours");
    expect(badge.className).toContain("blue");
  });

  it("applique la couleur grise pour un statut inconnu", () => {
    render(<StatusBadge status="inconnu" />);
    const badge = screen.getByText("inconnu");
    expect(badge.className).toContain("gray");
  });
});
