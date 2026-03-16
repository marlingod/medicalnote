import { describe, it, expect } from "vitest";
import {
  useEncounters,
  useEncounter,
  useCreateEncounter,
  usePasteInput,
  useUploadRecording,
  useUploadScan,
} from "@/hooks/use-encounters";

describe("Encounter hooks", () => {
  it("exports all encounter hook functions", () => {
    expect(useEncounters).toBeInstanceOf(Function);
    expect(useEncounter).toBeInstanceOf(Function);
    expect(useCreateEncounter).toBeInstanceOf(Function);
    expect(usePasteInput).toBeInstanceOf(Function);
    expect(useUploadRecording).toBeInstanceOf(Function);
    expect(useUploadScan).toBeInstanceOf(Function);
  });
});
