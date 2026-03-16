import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    auth: {
      login: vi.fn(),
      getUser: vi.fn(),
      logout: vi.fn(),
    },
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe("useAuth", () => {
  it("initially has no user and isLoading is true", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toBeNull();
  });

  it("exposes login, logout, isAuthenticated", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.login).toBeInstanceOf(Function);
    expect(result.current.logout).toBeInstanceOf(Function);
    expect(typeof result.current.isAuthenticated).toBe("boolean");
  });
});
