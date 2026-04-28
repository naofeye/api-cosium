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

describe("SendDocumentEmailDialog (facture)", () => {
  beforeEach(() => {
    mockToast.mockClear();
    mockFetchJson.mockReset();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("affiche le bon header pour une facture", () => {
    render(
      <SendDocumentEmailDialog
        open={true}
        onClose={() => {}}
        endpoint="/factures/7/send-email"
        documentNumero="F-00007"
        documentLabel="facture"
        defaultRecipient="client@example.com"
      />,
    );
    expect(
      screen.getByRole("heading", { name: /envoyer la facture F-00007/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/PDF de la facture sera attache/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Votre facture F-00007")).toBeInTheDocument();
  });

  it("envoie vers l'endpoint factures et toast 'Facture envoye a ...'", async () => {
    mockFetchJson.mockResolvedValueOnce({
      sent: true,
      to: "client@example.com",
      facture_id: 7,
    });
    const onClose = vi.fn();

    render(
      <SendDocumentEmailDialog
        open={true}
        onClose={onClose}
        endpoint="/factures/7/send-email"
        documentNumero="F-00007"
        documentLabel="facture"
        defaultRecipient="client@example.com"
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /^envoyer$/i }));

    await waitFor(() => {
      expect(mockFetchJson).toHaveBeenCalledWith(
        "/factures/7/send-email",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(mockToast).toHaveBeenCalledWith(
      expect.stringMatching(/Facture envoye/),
      "success",
    );
    expect(onClose).toHaveBeenCalled();
  });

  it("desactive le bouton si l'email est invalide", () => {
    render(
      <SendDocumentEmailDialog
        open={true}
        onClose={() => {}}
        endpoint="/factures/1/send-email"
        documentNumero="F-00001"
        documentLabel="facture"
        defaultRecipient="bad-email"
      />,
    );
    expect(screen.getByRole("button", { name: /^envoyer$/i })).toBeDisabled();
  });
});
