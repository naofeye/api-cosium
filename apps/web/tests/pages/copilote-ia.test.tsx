import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";

const mockToast = vi.fn();
vi.mock("@/components/ui/Toast", () => ({
  useToast: () => ({ toast: mockToast }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => "/copilote-ia",
}));

vi.mock("@/components/layout/PageLayout", () => ({
  PageLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));

import { ChatInterface } from "@/app/copilote-ia/components/ChatInterface";

function buildSseStream(frames: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const frame of frames) {
        controller.enqueue(encoder.encode(frame));
      }
      controller.close();
    },
  });
}

function mockFetchOnce(frames: string[], status = 200) {
  const body = buildSseStream(frames);
  const response = new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
  vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(response));
}

describe("ChatInterface", () => {
  beforeEach(() => {
    mockToast.mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("affiche l'etat vide avec le texte d'aide", () => {
    render(<ChatInterface />);
    expect(
      screen.getByRole("heading", { name: /posez une question/i }),
    ).toBeInTheDocument();
  });

  it("expose les 4 modes du copilote dans le select", () => {
    render(<ChatInterface />);
    const select = screen.getByLabelText(/sélectionner le mode/i);
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /dossier/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /financier/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /documentaire/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /marketing/i })).toBeInTheDocument();
  });

  it("desactive le bouton envoyer quand l'input est vide", () => {
    render(<ChatInterface />);
    const sendBtn = screen.getByRole("button", { name: /envoyer la question/i });
    expect(sendBtn).toBeDisabled();
  });

  it("envoie une question et affiche les chunks streames", async () => {
    mockFetchOnce([
      'event: chunk\ndata: {"text": "Bonjour "}\n\n',
      'event: chunk\ndata: {"text": "Nabil"}\n\n',
      'event: done\ndata: {"tokens_in": 5, "tokens_out": 3, "model": "claude-test"}\n\n',
    ]);

    render(<ChatInterface />);

    const textarea = screen.getByLabelText(/votre question/i);
    fireEvent.change(textarea, { target: { value: "Salut" } });

    const sendBtn = screen.getByRole("button", { name: /envoyer la question/i });
    fireEvent.click(sendBtn);

    await waitFor(() => {
      expect(screen.getByText(/Bonjour Nabil/)).toBeInTheDocument();
    });
    expect(screen.getByText("Salut")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/ai/copilot/stream"),
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      }),
    );
  });

  it("affiche un message d'erreur quand le serveur emet un event error", async () => {
    mockFetchOnce([
      'event: error\ndata: {"error": "[Erreur IA] Service indisponible."}\n\n',
    ]);

    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText(/votre question/i), {
      target: { value: "Test" },
    });
    fireEvent.click(screen.getByRole("button", { name: /envoyer la question/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Service indisponible");
    });
  });

  it("affiche une erreur quand le fetch echoue", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValueOnce(new Error("Network down")));

    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText(/votre question/i), {
      target: { value: "Hello" },
    });
    fireEvent.click(screen.getByRole("button", { name: /envoyer la question/i }));

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith("Network down", "error");
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Network down");
  });

  it("efface l'historique via le bouton Effacer", async () => {
    mockFetchOnce([
      'event: chunk\ndata: {"text": "Reponse"}\n\n',
      'event: done\ndata: {"tokens_in": 1, "tokens_out": 1, "model": "test"}\n\n',
    ]);

    render(<ChatInterface />);
    fireEvent.change(screen.getByLabelText(/votre question/i), {
      target: { value: "Question" },
    });
    fireEvent.click(screen.getByRole("button", { name: /envoyer la question/i }));

    await waitFor(() => {
      expect(screen.getByText("Reponse")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /effacer la conversation/i }));

    expect(screen.queryByText("Reponse")).not.toBeInTheDocument();
    expect(screen.queryByText("Question")).not.toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: /posez une question/i }),
    ).toBeInTheDocument();
  });
});
