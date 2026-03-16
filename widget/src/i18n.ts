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

export const TRANSLATIONS: Record<"en" | "es", TranslationStrings> = {
  en: {
    title: "Visit Summary",
    subtitle_date: "Date",
    subtitle_doctor: "Provider",
    summary_heading: "Your Visit Summary",
    disclaimer_label: "Important Notice",
    tooltip_label: "What does this mean?",
    lang_en: "English",
    lang_es: "Español",
    loading: "Loading your visit summary...",
    error_expired:
      "This link has expired. Please request a new summary link from your clinic.",
    error_not_found: "Summary not found. Please check your link and try again.",
    error_network:
      "Unable to connect. Please check your internet connection and try again.",
    error_generic: "Something went wrong. Please try again later.",
    powered_by: "Powered by MedicalNote",
    enter_token_label: "Access Code",
    enter_token_placeholder: "Enter your access code",
    submit_button: "View Summary",
    medical_terms_heading: "Medical Terms Explained",
  },
  es: {
    title: "Resumen de la Visita",
    subtitle_date: "Fecha",
    subtitle_doctor: "Proveedor",
    summary_heading: "Su Resumen de Visita",
    disclaimer_label: "Aviso Importante",
    tooltip_label: "¿Qué significa esto?",
    lang_en: "English",
    lang_es: "Español",
    loading: "Cargando su resumen de visita...",
    error_expired:
      "Este enlace ha expirado. Solicite un nuevo enlace de resumen a su clínica.",
    error_not_found:
      "Resumen no encontrado. Verifique su enlace e intente de nuevo.",
    error_network:
      "No se puede conectar. Verifique su conexión a internet e intente de nuevo.",
    error_generic: "Algo salió mal. Intente de nuevo más tarde.",
    powered_by: "Desarrollado por MedicalNote",
    enter_token_label: "Código de Acceso",
    enter_token_placeholder: "Ingrese su código de acceso",
    submit_button: "Ver Resumen",
    medical_terms_heading: "Términos Médicos Explicados",
  },
};

export function getTranslation(lang: "en" | "es"): TranslationStrings {
  return TRANSLATIONS[lang] ?? TRANSLATIONS.en;
}
