import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";

import { useCollapsedGroups } from "@/components/layout/sidebar/useCollapsedGroups";

const STORAGE_KEY = "optiflow-sidebar-collapsed-groups";

describe("useCollapsedGroups", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("etat initial : tout ouvert (objet vide)", () => {
    const { result } = renderHook(() => useCollapsedGroups());
    expect(result.current.collapsedGroups).toEqual({});
  });

  it("toggleGroup ferme un groupe", () => {
    const { result } = renderHook(() => useCollapsedGroups());
    act(() => result.current.toggleGroup("finance"));
    expect(result.current.collapsedGroups.finance).toBe(true);
  });

  it("toggleGroup deux fois reouvre", () => {
    const { result } = renderHook(() => useCollapsedGroups());
    act(() => result.current.toggleGroup("finance"));
    act(() => result.current.toggleGroup("finance"));
    expect(result.current.collapsedGroups.finance).toBe(false);
  });

  it("toggleGroup persiste dans localStorage", () => {
    const { result } = renderHook(() => useCollapsedGroups());
    act(() => result.current.toggleGroup("admin"));
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    expect(stored.admin).toBe(true);
  });

  it("etat initial relit localStorage", () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ marketing: true }));
    const { result } = renderHook(() => useCollapsedGroups());
    expect(result.current.collapsedGroups.marketing).toBe(true);
  });

  it("groupes independants", () => {
    const { result } = renderHook(() => useCollapsedGroups());
    act(() => result.current.toggleGroup("finance"));
    act(() => result.current.toggleGroup("admin"));
    expect(result.current.collapsedGroups.finance).toBe(true);
    expect(result.current.collapsedGroups.admin).toBe(true);
  });

  it("localStorage corrompu = etat vide (pas de crash)", () => {
    localStorage.setItem(STORAGE_KEY, "{not valid json}");
    const { result } = renderHook(() => useCollapsedGroups());
    expect(result.current.collapsedGroups).toEqual({});
  });
});
