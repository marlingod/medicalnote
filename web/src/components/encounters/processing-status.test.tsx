import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProcessingStatus } from "@/components/encounters/processing-status";

vi.mock("@/hooks/use-job-status", () => ({
  useJobStatus: () => ({ status: "transcribing", isConnected: true, error: null }),
}));

describe("ProcessingStatus", () => {
  it("renders the current status step", () => {
    render(<ProcessingStatus encounterId="test" currentStatus="transcribing" />);
    expect(screen.getByText(/transcribing/i)).toBeInTheDocument();
  });
});
