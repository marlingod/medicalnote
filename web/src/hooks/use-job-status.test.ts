import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useJobStatus } from "@/hooks/use-job-status";

// Mock WebSocket
const mockWs = {
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1,
};
vi.stubGlobal("WebSocket", vi.fn(() => mockWs));

describe("useJobStatus", () => {
  it("returns status and isConnected", () => {
    const { result } = renderHook(() =>
      useJobStatus("test-encounter-id", { enabled: false })
    );
    expect(result.current.status).toBeNull();
    expect(result.current.isConnected).toBe(false);
  });

  it("does not connect when enabled is false", () => {
    renderHook(() => useJobStatus("test-id", { enabled: false }));
    expect(WebSocket).not.toHaveBeenCalled();
  });
});
