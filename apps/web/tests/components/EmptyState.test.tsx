import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "@/components/ui/EmptyState";

describe("EmptyState", () => {
  it("affiche le titre", () => {
    render(<EmptyState title="Aucun dossier" description="" />);
    expect(screen.getByText("Aucun dossier")).toBeInTheDocument();
  });

  it("affiche la description", () => {
    render(<EmptyState title="Vide" description="Commencez par creer un element." />);
    expect(screen.getByText("Commencez par creer un element.")).toBeInTheDocument();
  });

  it("affiche le bouton action si fourni", () => {
    render(<EmptyState title="Vide" description="Test" action={<button>Creer</button>} />);
    expect(screen.getByText("Creer")).toBeInTheDocument();
  });
});
