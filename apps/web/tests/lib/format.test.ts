import { describe, it, expect } from "vitest";
import { formatMoney, formatDate, formatPercent, formatPhone } from "@/lib/format";

describe("formatMoney", () => {
  it("formate un montant positif", () => {
    const result = formatMoney(1234.56);
    // Intl peut utiliser un espace insecable, on normalise
    expect(result.replace(/\s/g, " ")).toContain("1");
    expect(result).toContain("€");
  });

  it("formate zero", () => {
    const result = formatMoney(0);
    expect(result).toContain("0");
    expect(result).toContain("€");
  });

  it("formate un montant negatif", () => {
    const result = formatMoney(-500);
    expect(result).toContain("500");
  });
});

describe("formatDate", () => {
  it("formate une date string ISO", () => {
    const result = formatDate("2026-03-15T10:00:00Z");
    expect(result).toContain("15");
    expect(result).toContain("2026");
  });

  it("formate un objet Date", () => {
    const result = formatDate(new Date(2026, 2, 15));
    expect(result).toContain("15");
    expect(result).toContain("2026");
  });
});

describe("formatPercent", () => {
  it("formate un pourcentage", () => {
    const result = formatPercent(85.3);
    expect(result.replace(/\s/g, " ")).toContain("85");
    expect(result).toContain("%");
  });

  it("formate zero", () => {
    const result = formatPercent(0);
    expect(result).toContain("0");
    expect(result).toContain("%");
  });
});

describe("formatPhone", () => {
  it("formate un numero 10 chiffres", () => {
    expect(formatPhone("0612345678")).toBe("06 12 34 56 78");
  });

  it("retourne tel quel si pas 10 chiffres", () => {
    expect(formatPhone("+33612345678")).toBe("+33612345678");
  });

  it("gere les espaces existants", () => {
    expect(formatPhone("06 12 34 56 78")).toBe("06 12 34 56 78");
  });
});
