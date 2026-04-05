import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock EventSource before importing the module
const mockClose = vi.fn();
let mockOnMessage: ((event: MessageEvent) => void) | null = null;
let mockOnError: (() => void) | null = null;

class MockEventSource {
  url: string;
  withCredentials: boolean;
  close = mockClose;

  set onmessage(fn: ((event: MessageEvent) => void) | null) {
    mockOnMessage = fn;
  }
  set onerror(fn: (() => void) | null) {
    mockOnError = fn;
  }

  constructor(url: string, init?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = init?.withCredentials ?? false;
  }
}

vi.stubGlobal("EventSource", MockEventSource);

// Dynamic import to get fresh module state
let connectSSE: typeof import("@/lib/sse").connectSSE;
let disconnectSSE: typeof import("@/lib/sse").disconnectSSE;

describe("SSE", () => {
  beforeEach(async () => {
    vi.resetModules();
    mockClose.mockClear();
    mockOnMessage = null;
    mockOnError = null;
    const mod = await import("@/lib/sse");
    connectSSE = mod.connectSSE;
    disconnectSSE = mod.disconnectSSE;
  });

  afterEach(() => {
    disconnectSSE();
  });

  it("connectSSE cree un EventSource", () => {
    const handler = vi.fn();
    connectSSE(handler);
    // If EventSource was instantiated, mockOnMessage should be set
    expect(mockOnMessage).not.toBeNull();
  });

  it("disconnectSSE ferme la connexion", () => {
    const handler = vi.fn();
    connectSSE(handler);
    disconnectSSE();
    expect(mockClose).toHaveBeenCalled();
  });

  it("onNotification est appele a la reception d'un message", () => {
    const handler = vi.fn();
    connectSSE(handler);
    expect(mockOnMessage).not.toBeNull();
    const fakeEvent = { data: JSON.stringify({ id: 1, type: "info", title: "Test", message: "Hello", entity_type: null, entity_id: null, created_at: "2026-01-01" }) } as MessageEvent;
    mockOnMessage!(fakeEvent);
    expect(handler).toHaveBeenCalledWith(expect.objectContaining({ id: 1, title: "Test" }));
  });
});
