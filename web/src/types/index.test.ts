import { describe, it, expect } from "vitest";
import type {
  User,
  Practice,
  Patient,
  Encounter,
  Recording,
  Transcript,
  ClinicalNote,
  PatientSummary,
  PromptVersion,
  PaginatedResponse,
  EncounterStatus,
  InputMethod,
} from "@/types";

describe("Type definitions", () => {
  it("User type has required fields", () => {
    const user: User = {
      id: "uuid",
      email: "doc@test.com",
      first_name: "Jane",
      last_name: "Smith",
      role: "doctor",
      specialty: "Internal Medicine",
      license_number: "",
      practice: "uuid",
      practice_name: "Smith Clinic",
      language_preference: "en",
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(user.role).toBe("doctor");
  });

  it("Encounter type has required fields", () => {
    const encounter: Encounter = {
      id: "uuid",
      doctor: "uuid",
      patient: "uuid",
      encounter_date: "2026-03-15",
      input_method: "paste",
      status: "uploading",
      consent_recording: false,
      consent_timestamp: null,
      consent_method: "",
      consent_jurisdiction_state: "",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      has_recording: false,
      has_transcript: false,
      has_note: false,
      has_summary: false,
    };
    expect(encounter.status).toBe("uploading");
  });
});
