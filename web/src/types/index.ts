// ============ Auth Types ============

export type UserRole = "doctor" | "admin" | "patient";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  specialty: string;
  license_number: string;
  practice: string | null;
  practice_name: string | null;
  language_preference: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access: string;
  refresh: string;
  user: User;
}

export interface RegisterRequest {
  email: string;
  password1: string;
  password2: string;
  first_name: string;
  last_name: string;
  practice_name: string;
  specialty?: string;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
  refresh: string;
}

// ============ Practice Types ============

export type SubscriptionTier = "solo" | "group" | "enterprise";

export interface Practice {
  id: string;
  name: string;
  address: string;
  phone: string;
  subscription_tier: SubscriptionTier;
  white_label_config: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface PracticeStats {
  total_patients: number;
  total_encounters: number;
  encounters_by_status: Record<string, number>;
}

// ============ Patient Types ============

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  date_of_birth: string;
  language_preference: string;
  created_at: string;
  updated_at?: string;
}

export interface PatientListItem {
  id: string;
  first_name: string;
  last_name: string;
  language_preference: string;
  created_at: string;
}

export interface CreatePatientRequest {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  email?: string;
  phone?: string;
  language_preference?: string;
}

// ============ Encounter Types ============

export type EncounterStatus =
  | "uploading"
  | "transcribing"
  | "generating_note"
  | "generating_summary"
  | "ready_for_review"
  | "approved"
  | "delivered"
  | "transcription_failed"
  | "note_generation_failed"
  | "summary_generation_failed";

export type InputMethod = "recording" | "paste" | "dictation" | "scan";

export interface Encounter {
  id: string;
  doctor: string;
  patient: string;
  encounter_date: string;
  input_method: InputMethod;
  status: EncounterStatus;
  consent_recording: boolean;
  consent_timestamp: string | null;
  consent_method: string;
  consent_jurisdiction_state: string;
  created_at: string;
  updated_at: string;
  // Detail fields (optional, only in retrieve)
  has_recording?: boolean;
  has_transcript?: boolean;
  has_note?: boolean;
  has_summary?: boolean;
}

export interface CreateEncounterRequest {
  patient: string;
  encounter_date: string;
  input_method: InputMethod;
  consent_recording?: boolean;
  consent_method?: string;
  consent_jurisdiction_state?: string;
}

// ============ Recording / Transcript Types ============

export interface Recording {
  id: string;
  storage_url: string;
  duration_seconds: number;
  file_size_bytes: number;
  format: "wav" | "mp3" | "webm";
  transcription_status: "pending" | "processing" | "completed" | "failed";
  created_at: string;
}

export interface SpeakerSegment {
  speaker: string;
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  id: string;
  raw_text: string;
  speaker_segments: SpeakerSegment[];
  medical_terms_detected: string[];
  confidence_score: number;
  language_detected: string;
  created_at: string;
}

// ============ Clinical Note Types ============

export type NoteType = "soap" | "free_text" | "h_and_p";

export interface ClinicalNote {
  id: string;
  encounter: string;
  note_type: NoteType;
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
  raw_content: string;
  icd10_codes: string[];
  cpt_codes: string[];
  ai_generated: boolean;
  doctor_edited: boolean;
  approved_at: string | null;
  approved_by: string | null;
  prompt_version: string | null;
  prompt_version_detail: PromptVersion | null;
  created_at: string;
  updated_at: string;
}

export interface UpdateNoteRequest {
  subjective?: string;
  objective?: string;
  assessment?: string;
  plan?: string;
  doctor_edited?: boolean;
  note_type?: NoteType;
}

// ============ Summary Types ============

export type ReadingLevel = "grade_5" | "grade_8" | "grade_12";
export type DeliveryStatus = "pending" | "sent" | "viewed" | "failed";
export type DeliveryMethod = "app" | "widget" | "sms_link" | "email_link";

export interface MedicalTermExplanation {
  term: string;
  explanation: string;
}

export interface PatientSummary {
  id: string;
  encounter: string;
  clinical_note: string;
  summary_en: string;
  summary_es: string;
  reading_level: ReadingLevel;
  medical_terms_explained: MedicalTermExplanation[];
  disclaimer_text: string;
  delivery_status: DeliveryStatus;
  delivered_at: string | null;
  viewed_at: string | null;
  delivery_method: string;
  prompt_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface SendSummaryRequest {
  delivery_method: DeliveryMethod;
}

// ============ Prompt Version Types ============

export interface PromptVersion {
  id: string;
  prompt_name: string;
  version: string;
  is_active: boolean;
  created_at: string;
}

// ============ Pagination Types ============

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// ============ WebSocket Types ============

export interface JobStatusUpdate {
  type: "status_update";
  status: EncounterStatus;
  encounter_id: string;
}

// ============ Audit Types ============

export interface AuditLogEntry {
  id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  ip_address: string;
  phi_accessed: boolean;
  created_at: string;
}

// ============ Specialty Types ============

export type MedicalSpecialty =
  | "primary_care"
  | "dermatology"
  | "psychiatry"
  | "cardiology"
  | "orthopedics"
  | "pediatrics"
  | "neurology"
  | "gastroenterology"
  | "general";

export interface SpecialtyInfo {
  value: MedicalSpecialty;
  label: string;
  template_count: number;
}

// ============ Template Types ============

export type TemplateVisibility = "private" | "practice" | "public";
export type TemplateStatus = "draft" | "published" | "archived";

export interface TemplateSchemaField {
  key: string;
  label: string;
  type: "text" | "textarea" | "checklist" | "select";
  required?: boolean;
  ai_prompt?: string;
  options?: string[];
  conditional?: {
    show_if?: Record<string, string>;
  };
}

export interface TemplateSchemaSection {
  key: string;
  label: string;
  fields: TemplateSchemaField[];
  default_content?: string;
}

export interface TemplateSchema {
  sections: TemplateSchemaSection[];
  conditional_logic?: Array<{
    if: Record<string, string>;
    then: Record<string, string>;
  }>;
  ai_instructions?: string;
}

export interface TemplateRating {
  id: string;
  template: string;
  user: string;
  user_name: string;
  score: number;
  review: string;
  created_at: string;
}

export interface NoteTemplateListItem {
  id: string;
  name: string;
  description: string;
  specialty: MedicalSpecialty;
  note_type: NoteType;
  visibility: TemplateVisibility;
  status: TemplateStatus;
  version: number;
  tags: string[];
  use_count: number;
  clone_count: number;
  average_rating: number | null;
  rating_count: number;
  is_favorited: boolean;
  author_name: string;
  created_at: string;
  updated_at: string;
}

export interface NoteTemplate extends NoteTemplateListItem {
  schema: TemplateSchema;
  ratings: TemplateRating[];
}

export interface CreateTemplateRequest {
  name: string;
  description?: string;
  specialty: MedicalSpecialty;
  note_type: NoteType;
  schema: TemplateSchema;
  visibility?: TemplateVisibility;
  status?: TemplateStatus;
  tags?: string[];
}

export interface UpdateTemplateRequest extends Partial<CreateTemplateRequest> {}

export interface CloneTemplateRequest {
  name?: string;
}

export interface RateTemplateRequest {
  score: number;
  review?: string;
}

export interface AutoCompleteRequest {
  section_key: string;
  field_key?: string;
  encounter_context?: Record<string, unknown>;
  partial_content?: string;
}

export interface AutoCompleteResponse {
  content: string;
  section_key: string;
  field_key: string;
}

// ============ Quality Score Types ============

export type QualityScoreLevel =
  | "excellent"
  | "good"
  | "fair"
  | "needs_improvement";

export interface QualityCategoryScore {
  score: number;
  max_score: number;
  items_found: string[];
  items_missing: string[];
}

export interface QualityFinding {
  category: string;
  element: string;
  status: "present" | "missing" | "partial";
  detail?: string;
  suggestion?: string;
}

export interface QualityScore {
  id: string;
  clinical_note: string;
  encounter: string;
  overall_score: number;
  score_level: QualityScoreLevel;
  category_scores: Record<string, QualityCategoryScore>;
  findings: QualityFinding[];
  suggestions: string[];
  em_level_suggested: string;
  em_level_documented: string;
  rules_version: string;
  scored_at: string;
  updated_at: string;
}
