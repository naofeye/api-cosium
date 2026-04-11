import { describe, it, expect, vi, beforeEach } from "vitest";
import { downloadPdf } from "@/lib/download";

const mockCreateObjectURL = vi.fn(() => "blob:http://localhost/fake-url");
const mockRevokeObjectURL = vi.fn();

beforeEach(() => {
  vi.restoreAllMocks();
  global.URL.createObjectURL = mockCreateObjectURL;
  global.URL.revokeObjectURL = mockRevokeObjectURL;
});

describe("downloadPdf", () => {
  it("cree un blob et declenche le telechargement", async () => {
    const mockBlob = new Blob(["pdf content"], { type: "application/pdf" });
    const mockResponse = { ok: true, blob: () => Promise.resolve(mockBlob) };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    const mockClick = vi.fn();
    const mockAppendChild = vi.fn();
    const mockRemoveChild = vi.fn();
    const mockElement = { href: "", download: "", click: mockClick } as unknown as HTMLAnchorElement;

    vi.spyOn(document, "createElement").mockReturnValue(mockElement as unknown as HTMLAnchorElement);
    vi.spyOn(document.body, "appendChild").mockImplementation(mockAppendChild);
    vi.spyOn(document.body, "removeChild").mockImplementation(mockRemoveChild);

    await downloadPdf("/factures/1/pdf", "facture-1.pdf");

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/factures/1/pdf"),
      expect.objectContaining({ credentials: "include" }),
    );
    expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
    expect(mockClick).toHaveBeenCalled();
    expect(mockElement.download).toBe("facture-1.pdf");
    expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:http://localhost/fake-url");
  });

  it("lance une erreur sur une reponse non-200", async () => {
    const mockResponse = { ok: false, status: 404 };
    global.fetch = vi.fn().mockResolvedValue(mockResponse);

    await expect(downloadPdf("/factures/999/pdf", "facture.pdf")).rejects.toThrow(
      "Impossible de telecharger le PDF",
    );
  });
});
