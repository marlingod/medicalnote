/** Configuration read from data-* attributes on the script tag */
export interface WidgetEmbedConfig {
  widgetKey: string;
  theme: "light" | "dark";
  lang: "en" | "es";
  apiBaseUrl: string;
  containerId: string;
}

/** Branding config returned from GET /api/v1/widget/config/:widget_key */
export interface WidgetBrandConfig {
  logo_url: string;
  brand_color: string;
  custom_domain: string;
  practice_name: string;
  widget_key: string;
}

/** A single medical term with explanation */
export interface MedicalTermExplained {
  term: string;
  explanation: string;
}

/** Summary data returned from GET /api/v1/widget/summary/:token */
export interface WidgetSummaryData {
  id: string;
  summary_en: string;
  summary_es: string;
  reading_level: "grade_5" | "grade_8" | "grade_12";
  medical_terms_explained: MedicalTermExplained[];
  disclaimer_text: string;
  encounter_date: string;
  doctor_name: string;
  delivery_status: "pending" | "sent" | "viewed" | "failed";
  viewed_at: string | null;
  created_at: string;
}

/** Messages sent from host page script to iframe via postMessage */
export type HostToIframeMessage =
  | { type: "INIT"; config: WidgetEmbedConfig }
  | { type: "SET_TOKEN"; token: string }
  | { type: "SET_LANG"; lang: "en" | "es" };

/** Messages sent from iframe back to host page */
export type IframeToHostMessage =
  | { type: "READY" }
  | { type: "LOADED"; summaryId: string }
  | { type: "ERROR"; code: string; message: string }
  | { type: "RESIZE"; height: number };

/** Theme variables applied to iframe content */
export interface ThemeVariables {
  "--mn-brand-color": string;
  "--mn-bg-color": string;
  "--mn-text-color": string;
  "--mn-text-secondary": string;
  "--mn-border-color": string;
  "--mn-surface-color": string;
  "--mn-tooltip-bg": string;
  "--mn-tooltip-text": string;
  "--mn-font-family": string;
}

/** API error response shape */
export interface ApiError {
  error: string;
}
