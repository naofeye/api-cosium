import { describe, it, expect, vi, beforeEach } from "vitest";
import { exportToCsv } from "@/lib/export-csv";

describe("exportToCsv", () => {
  let mockClick: ReturnType<typeof vi.fn>;
  let capturedBlob: Blob | null;

  beforeEach(() => {
    mockClick = vi.fn();
    capturedBlob = null;

    vi.spyOn(URL, "createObjectURL").mockImplementation((blob: Blob) => {
      capturedBlob = blob;
      return "blob:test";
    });
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
    vi.spyOn(document, "createElement").mockReturnValue({
      href: "",
      download: "",
      click: mockClick,
    } as unknown as HTMLAnchorElement);
  });

  it("cree un Blob et declenche le telechargement", () => {
    exportToCsv("test.csv", ["Nom", "Prenom"], [["Dupont", "Jean"]]);
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(mockClick).toHaveBeenCalled();
  });

  it("utilise le point-virgule comme separateur", async () => {
    exportToCsv("test.csv", ["A", "B"], [["1", "2"]]);
    expect(capturedBlob).not.toBeNull();
    const text = await capturedBlob!.text();
    expect(text).toContain("A;B");
    expect(text).toContain("1;2");
  });

  it("inclut le BOM pour Excel", async () => {
    exportToCsv("test.csv", ["Col"], [["val"]]);
    expect(capturedBlob).not.toBeNull();
    const buffer = await capturedBlob!.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    // UTF-8 BOM = EF BB BF
    expect(bytes[0]).toBe(0xef);
    expect(bytes[1]).toBe(0xbb);
    expect(bytes[2]).toBe(0xbf);
  });
});
