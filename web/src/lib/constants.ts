export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws";

export const APP_NAME = "MedicalNote";

export const SUPPORTED_AUDIO_FORMATS = ["audio/wav", "audio/mp3", "audio/webm"] as const;

export const MAX_RECORDING_DURATION_MS = 120 * 60 * 1000; // 120 minutes

export const MAX_PASTE_LENGTH = 50_000;

export const ENCOUNTER_STATUSES = {
  uploading: "Uploading",
  transcribing: "Transcribing",
  generating_note: "Generating Note",
  generating_summary: "Generating Summary",
  ready_for_review: "Ready for Review",
  approved: "Approved",
  delivered: "Delivered",
  transcription_failed: "Transcription Failed",
  note_generation_failed: "Note Generation Failed",
  summary_generation_failed: "Summary Generation Failed",
} as const;
