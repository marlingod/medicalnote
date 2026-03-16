export interface TranslationStrings {
    title: string;
    subtitle_date: string;
    subtitle_doctor: string;
    summary_heading: string;
    disclaimer_label: string;
    tooltip_label: string;
    lang_en: string;
    lang_es: string;
    loading: string;
    error_expired: string;
    error_not_found: string;
    error_network: string;
    error_generic: string;
    powered_by: string;
    enter_token_label: string;
    enter_token_placeholder: string;
    submit_button: string;
    medical_terms_heading: string;
}
export declare const TRANSLATIONS: Record<"en" | "es", TranslationStrings>;
export declare function getTranslation(lang: "en" | "es"): TranslationStrings;
