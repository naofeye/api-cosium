import { describe, it, expect, vi, beforeEach } from "vitest";
import { toggleDarkMode, initTheme } from "@/lib/theme";

describe("theme", () => {
  beforeEach(() => {
    document.documentElement.classList.remove("dark");
    localStorage.clear();
  });

  it("toggleDarkMode ajoute et retire la classe .dark", () => {
    const result1 = toggleDarkMode();
    expect(result1).toBe(true);
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    const result2 = toggleDarkMode();
    expect(result2).toBe(false);
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("initTheme lit le theme depuis localStorage", () => {
    localStorage.setItem("theme", "dark");
    initTheme();
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("le dark mode est persiste dans localStorage", () => {
    toggleDarkMode();
    expect(localStorage.getItem("theme")).toBe("dark");
    toggleDarkMode();
    expect(localStorage.getItem("theme")).toBe("light");
  });
});
