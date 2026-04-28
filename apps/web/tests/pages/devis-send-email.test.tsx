import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockToast = vi.fn();
const mockFetchJson = vi.fn();

vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("@/lib/api", () => ({
  fetchJson: (...args: unknown[]) => mockFetchJson(...args),
}));

import { DevisSendEmailDialog } from "@/app/devis/[id]/components/DevisSendEmailDialog";

describe("DevisSendEmailDialog", () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockFetchJson.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("ne s'affiche pas quand open=false", () => {
    render(
      <DevisSendEmailDialog
        open={false}
        onClose={() => {}}
        devisId={1}
        devisNumero="DEV-00001"
        defaultRecipient="client@example.com"
      />,
    );
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("pre-remplit le destinataire avec l'email du client", () => {
    render(
      <DevisSendEmailDialog
        open={true}
        onClose={() => {}}
        devisId={42}
        devisNumero="DEV-00042"
        defaultRecipient="client@example.com"
      />,
    );
    const input = screen.getByLabelText(/destinataire/i) as HTMLInputElement;
    expect(input.value).toBe("client@example.com");
    expect(screen.getByDisplayValue("Votre devis DEV-00042")).toBeInTheDocument();
  });

  it("affiche un avertissement quand le client n'a pas d'email", () => {
    render(
      <DevisSendEmailDialog
        open={true}
        onClose={() => {}}
        devisId={1}
        devisNumero="DEV-00001"
        defaultRecipient={null}
      />,
    );
    expect(
      screen.getByText(/n'a pas d'email enregistre/i),
    ).toBeInTheDocument();
  });

  it("desactive le bouton envoyer pour un email invalide", () => {
    render(
      <DevisSendEmailDialog
        open={true}
        onClose={() => {}}
        devisId={1}
        devisNumero="DEV-00001"
        defaultRecipient="not-an-email"
      />,
    );
    const sendBtn = screen.getByRole("button", { name: /^envoyer$/i });
    expect(sendBtn).toBeDisabled();
  });

  it("envoie la requete avec to/subject/message et appelle onClose au succes", async () => {
    mockFetchJson.mockResolvedValueOnce({
      sent: true,
      to: "client@example.com",
      devis_id: 7,
    });
    const onClose = vi.fn();
    const onSent = vi.fn();

    render(
      <DevisSendEmailDialog
        open={true}
        onClose={onClose}
        devisId={7}
        devisNumero="DEV-00007"
        defaultRecipient="client@example.com"
        onSent={onSent}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /^envoyer$/i }));

    await waitFor(() => {
      expect(mockFetchJson).toHaveBeenCalledWith(
        "/devis/7/send-email",
        expect.objectContaining({ method: "POST" }),
      );
    });
    const callBody = JSON.parse(
      (mockFetchJson.mock.calls[0]?.[1] as { body: string }).body,
    );
    expect(callBody.to).toBe("client@example.com");
    expect(callBody.subject).toBe("Votre devis DEV-00007");
    expect(typeof callBody.message).toBe("string");

    expect(mockToast).toHaveBeenCalledWith(
      expect.stringContaining("client@example.com"),
      "success",
    );
    expect(onSent).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it("ne ferme pas le dialog si l'envoi echoue", async () => {
    mockFetchJson.mockRejectedValueOnce(new Error("API error"));
    const onClose = vi.fn();

    render(
      <DevisSendEmailDialog
        open={true}
        onClose={onClose}
        devisId={1}
        devisNumero="DEV-00001"
        defaultRecipient="client@example.com"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /^envoyer$/i }));

    await waitFor(() => {
      expect(mockFetchJson).toHaveBeenCalled();
    });
    expect(onClose).not.toHaveBeenCalled();
    expect(mockToast).not.toHaveBeenCalledWith(
      expect.anything(),
      "success",
    );
  });
});
