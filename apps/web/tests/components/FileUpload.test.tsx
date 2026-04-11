import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileUpload } from "@/components/ui/FileUpload";

describe("FileUpload", () => {
  it("affiche la zone d'upload avec le texte par defaut", () => {
    render(<FileUpload onFileSelect={vi.fn()} />);
    expect(screen.getByText("Glissez vos fichiers ici ou cliquez pour parcourir")).toBeInTheDocument();
  });

  it("affiche le nom du fichier apres selection", () => {
    const onFileSelect = vi.fn();
    const { container } = render(<FileUpload onFileSelect={onFileSelect} />);
    const input = container.querySelector("input[type='file']") as HTMLInputElement;
    const file = new File(["content"], "rapport.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByText("rapport.pdf")).toBeInTheDocument();
    expect(onFileSelect).toHaveBeenCalledWith(file);
  });

  it("a le style de zone de depot (bordure dashed)", () => {
    const { container } = render(<FileUpload onFileSelect={vi.fn()} />);
    const zone = container.firstElementChild as HTMLElement;
    expect(zone.className).toContain("border-dashed");
  });
});
