import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "@/components/ui/Button";

describe("Button", () => {
  it("rend le texte enfant", () => {
    render(<Button>Cliquer</Button>);
    expect(screen.getByText("Cliquer")).toBeInTheDocument();
  });

  it("applique la variante primary par defaut", () => {
    render(<Button>Test</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-primary");
  });

  it("applique la variante outline", () => {
    render(<Button variant="outline">Test</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("border");
  });

  it("applique la variante danger", () => {
    render(<Button variant="danger">Supprimer</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("bg-danger");
  });

  it("applique la taille sm", () => {
    render(<Button size="sm">Petit</Button>);
    const btn = screen.getByRole("button");
    expect(btn.className).toContain("text-xs");
  });

  it("est desactive quand disabled", () => {
    render(<Button disabled>Desactive</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("est desactive pendant le loading", () => {
    render(<Button loading>Chargement</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("affiche un spinner pendant le loading", () => {
    render(<Button loading>Envoi</Button>);
    const btn = screen.getByRole("button");
    expect(btn.querySelector("svg")).toBeTruthy();
  });

  it("appelle onClick au clic", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Clic</Button>);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("n'appelle pas onClick quand disabled", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(
      <Button onClick={onClick} disabled>
        Clic
      </Button>,
    );
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
