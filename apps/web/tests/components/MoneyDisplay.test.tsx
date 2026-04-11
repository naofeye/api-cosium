import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { MoneyDisplay } from "@/components/ui/MoneyDisplay";

describe("MoneyDisplay", () => {
  it("affiche un montant avec le symbole euro", () => {
    const { container } = render(<MoneyDisplay amount={1234.56} />);
    const text = container.textContent ?? "";
    expect(text).toContain("€");
  });

  it("affiche zero avec euro", () => {
    const { container } = render(<MoneyDisplay amount={0} />);
    const text = container.textContent ?? "";
    expect(text).toContain("€");
    expect(text).toContain("0");
  });

  it("applique la classe bold si bold=true", () => {
    const { container } = render(<MoneyDisplay amount={100} bold />);
    expect(container.firstChild).toHaveClass("font-semibold");
  });

  it("applique la classe success si colored et montant positif", () => {
    const { container } = render(<MoneyDisplay amount={100} colored />);
    expect(container.firstChild).toHaveClass("text-success");
  });

  it("applique la classe danger si colored et montant negatif", () => {
    const { container } = render(<MoneyDisplay amount={-50} colored />);
    expect(container.firstChild).toHaveClass("text-danger");
  });
});
