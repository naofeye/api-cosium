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

import { SendDocumentEmailDialog } from "@/components/ui/SendDocumentEmailDialog";

describe("SendDocumentEmailDialog (devis)", () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockFetchJson.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function renderDevisDialog(props: Partial<React.ComponentProps<typeof SendDocumentEmailDialog>> = {}) {
    return render(
      <SendDocumentEmailDialog
        open={true}
        onClose={() => {}}
        endpoint="/devis/42/send-email"
        documentNumero="DEV-00042"
        documentLabel="devis"
        defaultRecipient="client@example.com"
        {...props}
      />,
    );
  }

  it("ne s'affiche pas quand open=false", () => {
    renderDevisDialog({ open: false });
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("pre-remplit le destinataire avec l'email du client", () => {
    renderDevisDialog();
    const input = screen.getByLabelText(/destinataire/i) as HTMLInputElement;
    expect(input.value).toBe("client@example.com");
    expect(screen.getByDisplayValue("Votre devis DEV-00042")).toBeInTheDocument();
  });

  it("affiche un avertissement quand le client n'a pas d'email", () => {
    renderDevisDialog({ defaultRecipient: null });
    expect(
      screen.getByText(/n'a pas d'email enregistre/i),
    ).toBeInTheDocument();
  });

  it("desactive le bouton envoyer pour un email invalide", () => {
    renderDevisDialog({ defaultRecipient: "not-an-email" });
    const sendBtn = screen.getByRole("button", { name: /^envoyer$/i });
    expect(sendBtn).toBeDisabled();
  });

  it("envoie la requete avec to/subject/message et appelle onClose au succes", async () => {
    mockFetchJson.mockResolvedValueOnce({
      sent: true,
      to: "client@example.com",
      devis_id: 42,
    });
    const onClose = vi.fn();
    const onSent = vi.fn();

    renderDevisDialog({ onClose, onSent });

    fireEvent.click(screen.getByRole("button", { name: /^envoyer$/i }));

    await waitFor(() => {
      expect(mockFetchJson).toHaveBeenCalledWith(
        "/devis/42/send-email",
        expect.objectContaining({ method: "POST" }),
      );
    });
    const callBody = JSON.parse(
      (mockFetchJson.mock.calls[0]?.[1] as { body: string }).body,
    );
    expect(callBody.to).toBe("client@example.com");
    expect(callBody.subject).toBe("Votre devis DEV-00042");
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

    renderDevisDialog({ onClose });

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
