import { describe, it, expect } from "vitest";

describe("Project setup", () => {
  it("vitest is configured and running", () => {
    expect(true).toBe(true);
  });

  it("path alias @ resolves", async () => {
    // This will fail if the alias is misconfigured
    const mod = await import("@/lib/constants");
    expect(mod).toBeDefined();
  });
});
