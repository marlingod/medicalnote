import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthGuard } from "@/components/shared/auth-guard";

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ isAuthenticated: true, isLoading: false }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("AuthGuard", () => {
  it("exports an AuthGuard component", () => {
    expect(AuthGuard).toBeDefined();
  });
});
