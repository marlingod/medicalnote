export interface OTPSendRequest {
  phone: string;
}

export interface OTPSendResponse {
  message: string;
}

export interface OTPVerifyRequest {
  phone: string;
  code: string;
}

export interface OTPVerifyResponse {
  access: string;
  refresh: string;
  user_id: string;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenRefreshResponse {
  access: string;
  refresh: string;
}

export interface MedicalTermExplanation {
  term: string;
  explanation: string;
}

export interface PatientSummary {
  id: string;
  summary_en: string;
  summary_es: string;
  reading_level: 'grade_5' | 'grade_8' | 'grade_12';
  medical_terms_explained: MedicalTermExplanation[];
  disclaimer_text: string;
  encounter_date: string; // ISO date string "YYYY-MM-DD"
  doctor_name: string;
  delivery_status: 'pending' | 'sent' | 'viewed' | 'failed';
  viewed_at: string | null;
  created_at: string; // ISO datetime
}

export interface PatientSummaryListResponse {
  count: number;
  results: PatientSummary[];
}

export interface PatientProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
  language_preference: string;
}

export interface DeviceTokenRequest {
  token: string;
  platform: 'ios' | 'android';
}

export interface ApiError {
  error: string;
}
