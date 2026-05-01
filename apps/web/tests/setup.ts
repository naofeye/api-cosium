import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock global de `next/navigation` : useRouter() exige un App Router
// monte (contexte Next), absent en jsdom. On expose un router stub avec
// les methodes les plus courantes (push, replace, refresh, prefetch, back,
// forward) qui sont des no-op verifiables. usePathname / useSearchParams
// retournent des valeurs vides par defaut. Override possible dans un test
// via `vi.mocked(useRouter).mockReturnValue(...)`.
vi.mock("next/navigation", async () => {
  const actual = await vi.importActual<typeof import("next/navigation")>(
    "next/navigation",
  );
  return {
    ...actual,
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      refresh: vi.fn(),
      prefetch: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
    }),
    usePathname: () => "/",
    useSearchParams: () => new URLSearchParams(),
  };
});
