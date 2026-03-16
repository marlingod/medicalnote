import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AudioRecorder } from "@/components/encounters/audio-recorder";

describe("AudioRecorder", () => {
  it("renders start recording button", () => {
    render(<AudioRecorder onRecordingComplete={vi.fn()} />);
    expect(screen.getByRole("button", { name: /start recording/i })).toBeInTheDocument();
  });
});
