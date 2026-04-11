import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";

describe("ConfirmDialog", () => {
  it("ne s'affiche pas quand open=false", () => {
    render(
      <ConfirmDialog open={false} title="Titre" message="Message" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.queryByText("Titre")).not.toBeInTheDocument();
  });

  it("s'affiche avec titre et message quand open=true", () => {
    render(
      <ConfirmDialog open={true} title="Supprimer ?" message="Action irreversible" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.getByText("Supprimer ?")).toBeInTheDocument();
    expect(screen.getByText("Action irreversible")).toBeInTheDocument();
  });

  it("appelle onCancel au clic sur Annuler", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog open={true} title="Test" message="Msg" onConfirm={vi.fn()} onCancel={onCancel} />,
    );
    await user.click(screen.getByText("Annuler"));
    expect(onCancel).toHaveBeenCalledOnce();
  });

  it("appelle onConfirm au clic sur Confirmer", async () => {
    const user = userEvent.setup();
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog open={true} title="Test" message="Msg" onConfirm={onConfirm} onCancel={vi.fn()} />,
    );
    await user.click(screen.getByText("Confirmer"));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it("affiche un label personnalise sur le bouton confirmer", () => {
    render(
      <ConfirmDialog open={true} title="T" message="M" confirmLabel="Oui, supprimer" onConfirm={vi.fn()} onCancel={vi.fn()} />,
    );
    expect(screen.getByText("Oui, supprimer")).toBeInTheDocument();
  });

  it("ferme avec la touche Escape", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog open={true} title="T" message="M" onConfirm={vi.fn()} onCancel={onCancel} />,
    );
    await user.keyboard("{Escape}");
    expect(onCancel).toHaveBeenCalledOnce();
  });
});
