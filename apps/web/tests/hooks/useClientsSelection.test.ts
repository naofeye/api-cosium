import { describe, expect, it } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useClientsSelection } from "@/app/clients/hooks/useClientsSelection";

describe("useClientsSelection", () => {
  it("etat initial : selectedIds vide", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggleOne ajoute un id", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleOne(2));
    expect(result.current.selectedIds.has(2)).toBe(true);
    expect(result.current.selectedIds.size).toBe(1);
  });

  it("toggleOne deux fois retire l'id", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleOne(2));
    act(() => result.current.toggleOne(2));
    expect(result.current.selectedIds.has(2)).toBe(false);
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggleAll selectionne tout", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleAll());
    expect(result.current.selectedIds.size).toBe(3);
    expect(result.current.selectedIds.has(1)).toBe(true);
    expect(result.current.selectedIds.has(2)).toBe(true);
    expect(result.current.selectedIds.has(3)).toBe(true);
  });

  it("toggleAll quand tout est selectionne deselectionne tout", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleAll());
    act(() => result.current.toggleAll());
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggleAll ne selectionne pas si liste vide", () => {
    const { result } = renderHook(() => useClientsSelection([]));
    act(() => result.current.toggleAll());
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("clear vide la selection", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleOne(1));
    act(() => result.current.toggleOne(2));
    expect(result.current.selectedIds.size).toBe(2);
    act(() => result.current.clear());
    expect(result.current.selectedIds.size).toBe(0);
  });

  it("toggleAll partiel : si certains sont selectionnes, selectionne tout", () => {
    const { result } = renderHook(() => useClientsSelection([1, 2, 3]));
    act(() => result.current.toggleOne(1));
    expect(result.current.selectedIds.size).toBe(1);
    act(() => result.current.toggleAll());
    // Implementation : ne selectionne tout QUE si len(prev) === len(allIds), sinon select all
    expect(result.current.selectedIds.size).toBe(3);
  });
});
