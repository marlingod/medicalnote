import axios, { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL } from "@/lib/constants";
import type {
  User,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  TokenRefreshResponse,
  Patient,
  PatientListItem,
  CreatePatientRequest,
  Encounter,
  CreateEncounterRequest,
  Transcript,
  ClinicalNote,
  UpdateNoteRequest,
  PatientSummary,
  SendSummaryRequest,
  Practice,
  PracticeStats,
  AuditLogEntry,
  PaginatedResponse,
  NoteTemplate,
  NoteTemplateListItem,
  CreateTemplateRequest,
  UpdateTemplateRequest,
  CloneTemplateRequest,
  RateTemplateRequest,
  AutoCompleteRequest,
  AutoCompleteResponse,
  TemplateRating,
  SpecialtyInfo,
  QualityScore,
} from "@/types";

function createAxiosInstance(): AxiosInstance {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    headers: { "Content-Type": "application/json" },
    withCredentials: true,
  });

  instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  });

  instance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      if (
        error.response?.status === 401 &&
        !originalRequest._retry &&
        typeof window !== "undefined"
      ) {
        originalRequest._retry = true;
        const refresh = localStorage.getItem("refresh_token");
        if (refresh) {
          try {
            const { data } = await axios.post<TokenRefreshResponse>(
              `${API_BASE_URL}/auth/token/refresh/`,
              { refresh }
            );
            localStorage.setItem("access_token", data.access);
            localStorage.setItem("refresh_token", data.refresh);
            originalRequest.headers.Authorization = `Bearer ${data.access}`;
            return instance(originalRequest);
          } catch {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            if (typeof window !== "undefined") {
              window.location.href = "/login";
            }
          }
        }
      }
      return Promise.reject(error);
    }
  );

  return instance;
}

const http = createAxiosInstance();

export const apiClient = {
  auth: {
    login: (data: LoginRequest) =>
      http.post<LoginResponse>("/auth/login/", data).then((r) => r.data),
    register: (data: RegisterRequest) =>
      http.post("/auth/registration/", data).then((r) => r.data),
    getUser: () => http.get<User>("/auth/user/").then((r) => r.data),
    refreshToken: (refresh: string) =>
      http
        .post<TokenRefreshResponse>("/auth/token/refresh/", { refresh })
        .then((r) => r.data),
    logout: () => http.post("/auth/logout/").then((r) => r.data),
  },

  patients: {
    list: (params?: Record<string, string>) =>
      http
        .get<PaginatedResponse<PatientListItem>>("/patients/", { params })
        .then((r) => r.data),
    get: (id: string) =>
      http.get<Patient>(`/patients/${id}/`).then((r) => r.data),
    create: (data: CreatePatientRequest) =>
      http.post<Patient>("/patients/", data).then((r) => r.data),
    update: (id: string, data: Partial<CreatePatientRequest>) =>
      http.patch<Patient>(`/patients/${id}/`, data).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/patients/${id}/`).then((r) => r.data),
  },

  encounters: {
    list: (params?: Record<string, string>) =>
      http
        .get<PaginatedResponse<Encounter>>("/encounters/", { params })
        .then((r) => r.data),
    get: (id: string) =>
      http.get<Encounter>(`/encounters/${id}/`).then((r) => r.data),
    create: (data: CreateEncounterRequest) =>
      http.post<Encounter>("/encounters/", data).then((r) => r.data),
    update: (id: string, data: Partial<Encounter>) =>
      http.patch<Encounter>(`/encounters/${id}/`, data).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/encounters/${id}/`).then((r) => r.data),
    pasteInput: (id: string, text: string) =>
      http
        .post<{ status: string; encounter_id: string }>(
          `/encounters/${id}/paste/`,
          { text }
        )
        .then((r) => r.data),
    dictationInput: (id: string, text: string) =>
      http
        .post<{ status: string; encounter_id: string }>(
          `/encounters/${id}/dictation/`,
          { text }
        )
        .then((r) => r.data),
    uploadRecording: (id: string, audioFile: File) => {
      const formData = new FormData();
      formData.append("audio", audioFile);
      return http
        .post<{ status: string; encounter_id: string }>(
          `/encounters/${id}/recording/`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        )
        .then((r) => r.data);
    },
    uploadScan: (id: string, imageFile: File) => {
      const formData = new FormData();
      formData.append("image", imageFile);
      return http
        .post<{ status: string; encounter_id: string }>(
          `/encounters/${id}/scan/`,
          formData,
          { headers: { "Content-Type": "multipart/form-data" } }
        )
        .then((r) => r.data);
    },
    getTranscript: (id: string) =>
      http.get<Transcript>(`/encounters/${id}/transcript/`).then((r) => r.data),
  },

  notes: {
    get: (encounterId: string) =>
      http
        .get<ClinicalNote>(`/encounters/${encounterId}/note/`)
        .then((r) => r.data),
    update: (encounterId: string, data: UpdateNoteRequest) =>
      http
        .patch<ClinicalNote>(`/encounters/${encounterId}/note/`, data)
        .then((r) => r.data),
    approve: (encounterId: string) =>
      http
        .post<ClinicalNote>(`/encounters/${encounterId}/note/approve/`)
        .then((r) => r.data),
  },

  summaries: {
    get: (encounterId: string) =>
      http
        .get<PatientSummary>(`/encounters/${encounterId}/summary/`)
        .then((r) => r.data),
    send: (encounterId: string, data: SendSummaryRequest) =>
      http
        .post<PatientSummary>(`/encounters/${encounterId}/summary/send/`, data)
        .then((r) => r.data),
  },

  practice: {
    get: () => http.get<Practice>("/practice/").then((r) => r.data),
    update: (data: Partial<Practice>) =>
      http.patch<Practice>("/practice/", data).then((r) => r.data),
    getStats: () =>
      http.get<PracticeStats>("/practice/stats/").then((r) => r.data),
    getAuditLog: (params?: Record<string, string>) =>
      http
        .get<PaginatedResponse<AuditLogEntry>>("/practice/audit-log/", {
          params,
        })
        .then((r) => r.data),
  },

  templates: {
    list: (params?: Record<string, string>) =>
      http
        .get<PaginatedResponse<NoteTemplateListItem>>("/templates/", { params })
        .then((r) => r.data),
    get: (id: string) =>
      http.get<NoteTemplate>(`/templates/${id}/`).then((r) => r.data),
    create: (data: CreateTemplateRequest) =>
      http.post<NoteTemplate>("/templates/", data).then((r) => r.data),
    update: (id: string, data: UpdateTemplateRequest) =>
      http.patch<NoteTemplate>(`/templates/${id}/`, data).then((r) => r.data),
    delete: (id: string) =>
      http.delete(`/templates/${id}/`).then((r) => r.data),
    clone: (id: string, data?: CloneTemplateRequest) =>
      http
        .post<NoteTemplate>(`/templates/${id}/clone/`, data || {})
        .then((r) => r.data),
    rate: (id: string, data: RateTemplateRequest) =>
      http
        .post<TemplateRating>(`/templates/${id}/rate/`, data)
        .then((r) => r.data),
    favorite: (id: string) =>
      http
        .post<{ favorited: boolean }>(`/templates/${id}/favorite/`)
        .then((r) => r.data),
    unfavorite: (id: string) =>
      http
        .delete<{ favorited: boolean }>(`/templates/${id}/favorite/`)
        .then((r) => r.data),
    autoComplete: (id: string, data: AutoCompleteRequest) =>
      http
        .post<AutoCompleteResponse>(`/templates/${id}/auto-complete/`, data)
        .then((r) => r.data),
    getSpecialties: () =>
      http
        .get<SpecialtyInfo[]>("/templates/specialties/")
        .then((r) => r.data),
    getFavorites: (params?: Record<string, string>) =>
      http
        .get<PaginatedResponse<NoteTemplateListItem>>("/templates/favorites/", {
          params,
        })
        .then((r) => r.data),
  },

  quality: {
    get: (encounterId: string) =>
      http
        .get<QualityScore>(`/encounters/${encounterId}/quality/`)
        .then((r) => r.data),
    trigger: (encounterId: string) =>
      http
        .post<{ status: string }>(`/encounters/${encounterId}/quality/score/`)
        .then((r) => r.data),
  },
};
