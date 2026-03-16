import { describe, it, expect } from "vitest";
import { useNote, useUpdateNote, useApproveNote } from "@/hooks/use-notes";

describe("Notes hooks", () => {
  it("exports all note hook functions", () => {
    expect(useNote).toBeInstanceOf(Function);
    expect(useUpdateNote).toBeInstanceOf(Function);
    expect(useApproveNote).toBeInstanceOf(Function);
  });
});
