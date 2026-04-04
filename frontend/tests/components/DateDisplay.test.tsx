import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { DateDisplay } from "@/components/ui/DateDisplay";

describe("DateDisplay", () => {
  it("affiche une date non vide pour une date valide", () => {
    const { container } = render(<DateDisplay date="2026-03-15T10:00:00Z" />);
    const text = container.textContent ?? "";
    expect(text.length).toBeGreaterThan(0);
    expect(text).not.toBe("—");
  });

  it("affiche un tiret pour null", () => {
    const { container } = render(<DateDisplay date={null} />);
    expect(container.textContent).toBe("—");
  });

  it("affiche un tiret pour undefined", () => {
    const { container } = render(<DateDisplay date={undefined} />);
    expect(container.textContent).toBe("—");
  });
});
