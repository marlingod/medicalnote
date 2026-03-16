import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EncountersList } from "./encounters-list";

vi.mock("@/hooks/use-encounters", () => ({
  useEncounters: () => ({
    data: {
      count: 2,
      results: [
        {
          id: "uuid-1",
          patient: "patient-1",
          encounter_date: "2026-03-15",
          input_method: "paste",
          status: "ready_for_review",
          created_at: "2026-03-15T10:00:00Z",
        },
        {
          id: "uuid-2",
          patient: "patient-2",
          encounter_date: "2026-03-14",
          input_method: "recording",
          status: "transcribing",
          created_at: "2026-03-14T14:00:00Z",
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
}));

describe("EncountersList", () => {
  it("renders a heading", () => {
    render(<EncountersList />);
    expect(screen.getByText(/encounters/i)).toBeInTheDocument();
  });

  it("renders encounter rows", () => {
    render(<EncountersList />);
    expect(screen.getByText("Ready for Review")).toBeInTheDocument();
    expect(screen.getByText("Transcribing")).toBeInTheDocument();
  });
});
