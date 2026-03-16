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

export const SPECIALTY_LABELS: Record<string, string> = {
  primary_care: "Primary Care",
  dermatology: "Dermatology",
  psychiatry: "Psychiatry",
  cardiology: "Cardiology",
  orthopedics: "Orthopedics",
  pediatrics: "Pediatrics",
  neurology: "Neurology",
  gastroenterology: "Gastroenterology",
  general: "General",
} as const;

export const QUALITY_SCORE_LEVELS: Record<string, string> = {
  excellent: "Excellent",
  good: "Good",
  fair: "Fair",
  needs_improvement: "Needs Improvement",
} as const;

export const QUALITY_SCORE_COLORS: Record<string, string> = {
  excellent: "bg-green-100 text-green-800",
  good: "bg-blue-100 text-blue-800",
  fair: "bg-yellow-100 text-yellow-800",
  needs_improvement: "bg-red-100 text-red-800",
} as const;

export const TEMPLATE_VISIBILITY_LABELS: Record<string, string> = {
  private: "Private",
  practice: "Practice",
  public: "Public (Marketplace)",
} as const;

export const TEMPLATE_STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  published: "Published",
  archived: "Archived",
} as const;
