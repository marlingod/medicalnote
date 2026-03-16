# Phase 1 Web Dashboard Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Next.js 15 Doctor Web Dashboard that consumes the Django backend API, providing encounter creation (record/paste/dictate/scan), real-time processing status via WebSocket, SOAP note review/editing, and patient summary delivery.

**Architecture:** Next.js 15 App Router with route groups `(auth)` and `(dashboard)`. Server-side rendering for initial page loads, client-side TanStack Query for data fetching and caching. WebSocket connection via a custom hook for real-time job status updates from the Django Channels backend at `ws://api/v1/ws/jobs/:encounter_id`. All API calls go through a typed Axios-based client matching the DRF endpoints.

**Tech Stack:** Next.js 15 (App Router), TypeScript 5.x, shadcn/ui, Tailwind CSS 4, TanStack Query v5, React Hook Form + Zod, MediaRecorder API + RecordRTC, native WebSocket, next-intl (i18n), Vitest + React Testing Library

---

## Chunk 1: Project Scaffolding and Configuration

### Task 1.1: Initialize Next.js 15 project with TypeScript and Tailwind

- [ ] **Step 1 (3 min):** Create the Next.js project with App Router, TypeScript, Tailwind CSS, and ESLint.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote
npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

- [ ] **Step 2 (2 min):** Install all required dependencies.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npm install @tanstack/react-query @tanstack/react-query-devtools axios react-hook-form @hookform/resolvers zod recordrtc next-intl clsx tailwind-merge lucide-react date-fns
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom @vitejs/plugin-react @types/recordrtc msw
```

- [ ] **Step 3 (2 min):** Initialize shadcn/ui.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npx shadcn@latest init -d
```

- [ ] **Step 4 (2 min):** Install core shadcn/ui components.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npx shadcn@latest add button input label card dialog select textarea badge tabs toast separator dropdown-menu avatar sheet form table skeleton alert
```

- [ ] **Step 5 (2 min):** Create Vitest configuration.

File: `web/vitest.config.ts`
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
```

File: `web/src/test/setup.ts`
```typescript
import "@testing-library/jest-dom/vitest";
```

Add to `web/package.json` scripts:
```json
{
  "scripts": {
    "test": "vitest",
    "test:run": "vitest run",
    "test:coverage": "vitest run --coverage"
  }
}
```

- [ ] **Step 6 (2 min):** Create the directory structure matching the architecture spec.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src
mkdir -p app/\(auth\)/login
mkdir -p app/\(auth\)/register
mkdir -p app/\(dashboard\)/encounters/new
mkdir -p app/\(dashboard\)/encounters/\[id\]
mkdir -p app/\(dashboard\)/patients
mkdir -p app/\(dashboard\)/patients/\[id\]
mkdir -p app/\(dashboard\)/settings
mkdir -p components/encounters
mkdir -p components/notes
mkdir -p components/patients
mkdir -p components/shared
mkdir -p components/ui
mkdir -p lib
mkdir -p hooks
mkdir -p types
mkdir -p test/mocks
mkdir -p i18n/messages
```

- [ ] **Step 7 (2 min):** Create environment configuration.

File: `web/.env.local.example`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
```

File: `web/.env.local`
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws
```

- [ ] **Step 8 (2 min):** Write and run a smoke test to verify the project boots.

File: `web/src/test/setup.test.ts`
```typescript
import { describe, it, expect } from "vitest";

describe("Project setup", () => {
  it("vitest is configured and running", () => {
    expect(true).toBe(true);
  });

  it("path alias @ resolves", async () => {
    // This will fail if the alias is misconfigured
    const mod = await import("@/lib/constants");
    expect(mod).toBeDefined();
  });
});
```

File: `web/src/lib/constants.ts`
```typescript
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
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 2: TypeScript Types and API Client

### Task 2.1: Define all TypeScript types matching backend models

- [ ] **Step 1 (3 min):** Write failing test for types existence.

File: `web/src/types/index.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import type {
  User,
  Practice,
  Patient,
  Encounter,
  Recording,
  Transcript,
  ClinicalNote,
  PatientSummary,
  PromptVersion,
  PaginatedResponse,
  EncounterStatus,
  InputMethod,
} from "@/types";

describe("Type definitions", () => {
  it("User type has required fields", () => {
    const user: User = {
      id: "uuid",
      email: "doc@test.com",
      first_name: "Jane",
      last_name: "Smith",
      role: "doctor",
      specialty: "Internal Medicine",
      license_number: "",
      practice: "uuid",
      practice_name: "Smith Clinic",
      language_preference: "en",
      created_at: "2026-01-01T00:00:00Z",
    };
    expect(user.role).toBe("doctor");
  });

  it("Encounter type has required fields", () => {
    const encounter: Encounter = {
      id: "uuid",
      doctor: "uuid",
      patient: "uuid",
      encounter_date: "2026-03-15",
      input_method: "paste",
      status: "uploading",
      consent_recording: false,
      consent_timestamp: null,
      consent_method: "",
      consent_jurisdiction_state: "",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
      has_recording: false,
      has_transcript: false,
      has_note: false,
      has_summary: false,
    };
    expect(encounter.status).toBe("uploading");
  });
});
```

- [ ] **Step 2 (4 min):** Implement all types.

File: `web/src/types/index.ts`
```typescript
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
```

Run: `cd web && npm run test:run`
Verify: All type tests pass.

### Task 2.2: Implement typed API client

- [ ] **Step 1 (3 min):** Write failing tests for the API client.

File: `web/src/lib/api-client.test.ts`
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiClient } from "@/lib/api-client";

// Mock axios
vi.mock("axios", () => {
  const mockAxios = {
    create: vi.fn(() => mockAxios),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  };
  return { default: mockAxios };
});

describe("API Client", () => {
  it("exports an apiClient object with all resource methods", () => {
    expect(apiClient).toBeDefined();
    expect(apiClient.auth).toBeDefined();
    expect(apiClient.patients).toBeDefined();
    expect(apiClient.encounters).toBeDefined();
    expect(apiClient.notes).toBeDefined();
    expect(apiClient.summaries).toBeDefined();
    expect(apiClient.practice).toBeDefined();
  });

  it("auth has login, register, user, refresh methods", () => {
    expect(apiClient.auth.login).toBeInstanceOf(Function);
    expect(apiClient.auth.register).toBeInstanceOf(Function);
    expect(apiClient.auth.getUser).toBeInstanceOf(Function);
    expect(apiClient.auth.refreshToken).toBeInstanceOf(Function);
    expect(apiClient.auth.logout).toBeInstanceOf(Function);
  });

  it("encounters has paste, recording, scan, dictation methods", () => {
    expect(apiClient.encounters.create).toBeInstanceOf(Function);
    expect(apiClient.encounters.list).toBeInstanceOf(Function);
    expect(apiClient.encounters.get).toBeInstanceOf(Function);
    expect(apiClient.encounters.pasteInput).toBeInstanceOf(Function);
    expect(apiClient.encounters.uploadRecording).toBeInstanceOf(Function);
    expect(apiClient.encounters.uploadScan).toBeInstanceOf(Function);
    expect(apiClient.encounters.dictationInput).toBeInstanceOf(Function);
    expect(apiClient.encounters.getTranscript).toBeInstanceOf(Function);
  });

  it("notes has get, update, approve methods", () => {
    expect(apiClient.notes.get).toBeInstanceOf(Function);
    expect(apiClient.notes.update).toBeInstanceOf(Function);
    expect(apiClient.notes.approve).toBeInstanceOf(Function);
  });

  it("summaries has get, send methods", () => {
    expect(apiClient.summaries.get).toBeInstanceOf(Function);
    expect(apiClient.summaries.send).toBeInstanceOf(Function);
  });
});
```

- [ ] **Step 2 (5 min):** Implement the full typed API client.

File: `web/src/lib/api-client.ts`
```typescript
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
};
```

Run: `cd web && npm run test:run`
Verify: All tests pass.

---

## Chunk 3: Auth Context, Providers, and Layout

### Task 3.1: Auth context with token management

- [ ] **Step 1 (3 min):** Write failing tests for auth context.

File: `web/src/lib/auth-context.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import React from "react";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    auth: {
      login: vi.fn(),
      getUser: vi.fn(),
      logout: vi.fn(),
    },
  },
}));

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AuthProvider>{children}</AuthProvider>
);

describe("useAuth", () => {
  it("initially has no user and isLoading is true", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.user).toBeNull();
  });

  it("exposes login, logout, isAuthenticated", () => {
    const { result } = renderHook(() => useAuth(), { wrapper });
    expect(result.current.login).toBeInstanceOf(Function);
    expect(result.current.logout).toBeInstanceOf(Function);
    expect(typeof result.current.isAuthenticated).toBe("boolean");
  });
});
```

- [ ] **Step 2 (4 min):** Implement auth context.

File: `web/src/lib/auth-context.tsx`
```typescript
"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { apiClient } from "@/lib/api-client";
import type { User, LoginRequest } from "@/types";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const userData = await apiClient.auth.getUser();
      setUser(userData);
    } catch {
      setUser(null);
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
    }
  }, []);

  useEffect(() => {
    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    if (token) {
      refreshUser().finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [refreshUser]);

  const login = async (credentials: LoginRequest) => {
    const response = await apiClient.auth.login(credentials);
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", response.access);
      localStorage.setItem("refresh_token", response.refresh);
    }
    await refreshUser();
  };

  const logout = async () => {
    try {
      await apiClient.auth.logout();
    } finally {
      if (typeof window !== "undefined") {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

### Task 3.2: Query client provider and root layout

- [ ] **Step 1 (3 min):** Create the app providers wrapper.

File: `web/src/lib/providers.tsx`
```typescript
"use client";

import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { AuthProvider } from "@/lib/auth-context";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30 * 1000, // 30 seconds
            retry: 1,
            refetchOnWindowFocus: false,
          },
          mutations: {
            retry: 0,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{children}</AuthProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2 (2 min):** Update the root layout.

File: `web/src/app/layout.tsx`
```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/lib/providers";
import { Toaster } from "@/components/ui/toaster";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MedicalNote - Doctor Dashboard",
  description: "AI-powered clinical documentation and patient summary platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>
          {children}
          <Toaster />
        </Providers>
      </body>
    </html>
  );
}
```

---

## Chunk 4: Auth Pages (Login + Register)

### Task 4.1: Login page with form validation

- [ ] **Step 1 (3 min):** Write failing tests for the login form.

File: `web/src/app/(auth)/login/login-form.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginForm } from "./login-form";

const mockLogin = vi.fn();
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login: mockLogin, isLoading: false }),
}));

describe("LoginForm", () => {
  it("renders email and password fields", () => {
    render(<LoginForm />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<LoginForm />);
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows validation errors for empty submit", async () => {
    render(<LoginForm />);
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText(/email is required/i)).toBeInTheDocument();
  });

  it("has a link to registration page", () => {
    render(<LoginForm />);
    expect(screen.getByText(/create an account/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 (4 min):** Implement the login form component.

File: `web/src/app/(auth)/login/login-form.tsx`
```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const loginSchema = z.object({
  email: z.string().min(1, "Email is required").email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginFormData) => {
    setError(null);
    try {
      await login(data);
      router.push("/encounters");
    } catch (err: unknown) {
      setError("Invalid email or password. Please try again.");
    }
  };

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Sign In</CardTitle>
        <CardDescription>Enter your credentials to access your dashboard</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" placeholder="doctor@clinic.com" {...register("email")} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" {...register("password")} />
            {errors.password && <p className="text-sm text-destructive">{errors.password.message}</p>}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in..." : "Sign In"}
          </Button>
          <p className="text-sm text-muted-foreground">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary underline">
              Create an account
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
```

- [ ] **Step 3 (2 min):** Create the login page and auth layout.

File: `web/src/app/(auth)/layout.tsx`
```typescript
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30 px-4">
      {children}
    </div>
  );
}
```

File: `web/src/app/(auth)/login/page.tsx`
```typescript
import { LoginForm } from "./login-form";

export default function LoginPage() {
  return <LoginForm />;
}
```

### Task 4.2: Registration page

- [ ] **Step 1 (3 min):** Write failing tests for the registration form.

File: `web/src/app/(auth)/register/register-form.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { RegisterForm } from "./register-form";

vi.mock("@/lib/api-client", () => ({
  apiClient: { auth: { register: vi.fn() } },
}));
vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ login: vi.fn(), isLoading: false }),
}));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe("RegisterForm", () => {
  it("renders all required registration fields", () => {
    render(<RegisterForm />);
    expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/practice name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/confirm password/i)).toBeInTheDocument();
  });

  it("renders a submit button", () => {
    render(<RegisterForm />);
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 (5 min):** Implement the registration form component.

File: `web/src/app/(auth)/register/register-form.tsx`
```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";

const registerSchema = z
  .object({
    first_name: z.string().min(1, "First name is required"),
    last_name: z.string().min(1, "Last name is required"),
    email: z.string().min(1, "Email is required").email("Invalid email"),
    practice_name: z.string().min(1, "Practice name is required"),
    specialty: z.string().optional(),
    password1: z.string().min(12, "Password must be at least 12 characters"),
    password2: z.string().min(1, "Please confirm your password"),
  })
  .refine((data) => data.password1 === data.password2, {
    message: "Passwords do not match",
    path: ["password2"],
  });

type RegisterFormData = z.infer<typeof registerSchema>;

export function RegisterForm() {
  const { login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setError(null);
    try {
      await apiClient.auth.register(data);
      await login({ email: data.email, password: data.password1 });
      router.push("/encounters");
    } catch (err: unknown) {
      setError("Registration failed. Please check your details and try again.");
    }
  };

  return (
    <Card className="w-full max-w-lg">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Create Account</CardTitle>
        <CardDescription>Set up your MedicalNote practice account</CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="first_name">First Name</Label>
              <Input id="first_name" {...register("first_name")} />
              {errors.first_name && <p className="text-sm text-destructive">{errors.first_name.message}</p>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="last_name">Last Name</Label>
              <Input id="last_name" {...register("last_name")} />
              {errors.last_name && <p className="text-sm text-destructive">{errors.last_name.message}</p>}
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" {...register("email")} />
            {errors.email && <p className="text-sm text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="practice_name">Practice Name</Label>
            <Input id="practice_name" placeholder="e.g. Downtown Family Clinic" {...register("practice_name")} />
            {errors.practice_name && <p className="text-sm text-destructive">{errors.practice_name.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="specialty">Specialty (optional)</Label>
            <Input id="specialty" placeholder="e.g. Internal Medicine" {...register("specialty")} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password1">Password</Label>
            <Input id="password1" type="password" {...register("password1")} />
            {errors.password1 && <p className="text-sm text-destructive">{errors.password1.message}</p>}
          </div>
          <div className="space-y-2">
            <Label htmlFor="password2">Confirm Password</Label>
            <Input id="password2" type="password" {...register("password2")} />
            {errors.password2 && <p className="text-sm text-destructive">{errors.password2.message}</p>}
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create Account"}
          </Button>
          <p className="text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link href="/login" className="text-primary underline">
              Sign in
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
```

File: `web/src/app/(auth)/register/page.tsx`
```typescript
import { RegisterForm } from "./register-form";

export default function RegisterPage() {
  return <RegisterForm />;
}
```

Run: `cd web && npm run test:run`
Verify: All tests pass.

---

## Chunk 5: Dashboard Layout and Navigation

### Task 5.1: Protected route wrapper and dashboard shell

- [ ] **Step 1 (3 min):** Write failing tests for the auth guard and sidebar.

File: `web/src/components/shared/auth-guard.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AuthGuard } from "@/components/shared/auth-guard";

describe("AuthGuard", () => {
  it("exports an AuthGuard component", () => {
    expect(AuthGuard).toBeDefined();
  });
});
```

- [ ] **Step 2 (4 min):** Implement the auth guard.

File: `web/src/components/shared/auth-guard.tsx`
```typescript
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Skeleton } from "@/components/ui/skeleton";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="space-y-4 w-64">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
```

- [ ] **Step 3 (5 min):** Implement the dashboard sidebar navigation.

File: `web/src/components/shared/sidebar.tsx`
```typescript
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  FileText,
  Users,
  PlusCircle,
  Settings,
  LogOut,
  Stethoscope,
} from "lucide-react";

const navItems = [
  { href: "/encounters", label: "Encounters", icon: FileText },
  { href: "/encounters/new", label: "New Encounter", icon: PlusCircle },
  { href: "/patients", label: "Patients", icon: Users },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="flex h-screen w-64 flex-col border-r bg-card">
      <div className="flex items-center gap-2 border-b px-6 py-4">
        <Stethoscope className="h-6 w-6 text-primary" />
        <span className="text-lg font-semibold">MedicalNote</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t px-3 py-4">
        <div className="mb-3 px-3">
          <p className="text-sm font-medium truncate">{user?.first_name} {user?.last_name}</p>
          <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
          {user?.practice_name && (
            <p className="text-xs text-muted-foreground truncate">{user.practice_name}</p>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-3 text-muted-foreground"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          Sign Out
        </Button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 4 (2 min):** Create the dashboard layout.

File: `web/src/app/(dashboard)/layout.tsx`
```typescript
import { AuthGuard } from "@/components/shared/auth-guard";
import { Sidebar } from "@/components/shared/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 6: WebSocket Hook for Real-Time Job Status

### Task 6.1: useJobStatus WebSocket hook

- [ ] **Step 1 (3 min):** Write failing tests.

File: `web/src/hooks/use-job-status.test.ts`
```typescript
import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useJobStatus } from "@/hooks/use-job-status";

// Mock WebSocket
const mockWs = {
  close: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  readyState: 1,
};
vi.stubGlobal("WebSocket", vi.fn(() => mockWs));

describe("useJobStatus", () => {
  it("returns status and isConnected", () => {
    const { result } = renderHook(() =>
      useJobStatus("test-encounter-id", { enabled: false })
    );
    expect(result.current.status).toBeNull();
    expect(result.current.isConnected).toBe(false);
  });

  it("does not connect when enabled is false", () => {
    renderHook(() => useJobStatus("test-id", { enabled: false }));
    expect(WebSocket).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2 (4 min):** Implement the WebSocket hook.

File: `web/src/hooks/use-job-status.ts`
```typescript
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { WS_BASE_URL } from "@/lib/constants";
import type { EncounterStatus, JobStatusUpdate } from "@/types";

interface UseJobStatusOptions {
  enabled?: boolean;
  onStatusChange?: (status: EncounterStatus) => void;
}

export function useJobStatus(
  encounterId: string | null,
  options: UseJobStatusOptions = {}
) {
  const { enabled = true, onStatusChange } = options;
  const [status, setStatus] = useState<EncounterStatus | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!encounterId || !enabled) return;

    const token =
      typeof window !== "undefined"
        ? localStorage.getItem("access_token")
        : null;
    if (!token) return;

    const wsUrl = `${WS_BASE_URL}/jobs/${encounterId}/?token=${token}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.addEventListener("open", () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      });

      ws.addEventListener("message", (event) => {
        try {
          const data: JobStatusUpdate = JSON.parse(event.data);
          if (data.type === "status_update") {
            setStatus(data.status);
            onStatusChange?.(data.status);
          }
        } catch {
          // Ignore malformed messages
        }
      });

      ws.addEventListener("close", () => {
        setIsConnected(false);
        // Auto-reconnect with exponential backoff
        if (
          enabled &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttemptsRef.current),
            30000
          );
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, delay);
        }
      });

      ws.addEventListener("error", () => {
        setError("WebSocket connection error");
      });
    } catch {
      setError("Failed to create WebSocket connection");
    }
  }, [encounterId, enabled, onStatusChange]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  return { status, isConnected, error, disconnect };
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 7: TanStack Query Hooks for Data Fetching

### Task 7.1: Encounter query hooks

- [ ] **Step 1 (3 min):** Write failing tests for encounter hooks.

File: `web/src/hooks/use-encounters.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import {
  useEncounters,
  useEncounter,
  useCreateEncounter,
  usePasteInput,
  useUploadRecording,
  useUploadScan,
} from "@/hooks/use-encounters";

describe("Encounter hooks", () => {
  it("exports all encounter hook functions", () => {
    expect(useEncounters).toBeInstanceOf(Function);
    expect(useEncounter).toBeInstanceOf(Function);
    expect(useCreateEncounter).toBeInstanceOf(Function);
    expect(usePasteInput).toBeInstanceOf(Function);
    expect(useUploadRecording).toBeInstanceOf(Function);
    expect(useUploadScan).toBeInstanceOf(Function);
  });
});
```

- [ ] **Step 2 (5 min):** Implement all encounter hooks.

File: `web/src/hooks/use-encounters.ts`
```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { CreateEncounterRequest } from "@/types";

export const encounterKeys = {
  all: ["encounters"] as const,
  lists: () => [...encounterKeys.all, "list"] as const,
  list: (params: Record<string, string>) =>
    [...encounterKeys.lists(), params] as const,
  details: () => [...encounterKeys.all, "detail"] as const,
  detail: (id: string) => [...encounterKeys.details(), id] as const,
  transcript: (id: string) =>
    [...encounterKeys.detail(id), "transcript"] as const,
};

export function useEncounters(params?: Record<string, string>) {
  return useQuery({
    queryKey: encounterKeys.list(params || {}),
    queryFn: () => apiClient.encounters.list(params),
  });
}

export function useEncounter(id: string) {
  return useQuery({
    queryKey: encounterKeys.detail(id),
    queryFn: () => apiClient.encounters.get(id),
    enabled: !!id,
  });
}

export function useTranscript(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: encounterKeys.transcript(encounterId),
    queryFn: () => apiClient.encounters.getTranscript(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useCreateEncounter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreateEncounterRequest) =>
      apiClient.encounters.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: encounterKeys.lists() });
    },
  });
}

export function usePasteInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiClient.encounters.pasteInput(id, text),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useDictationInput() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, text }: { id: string; text: string }) =>
      apiClient.encounters.dictationInput(id, text),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useUploadRecording() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      apiClient.encounters.uploadRecording(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}

export function useUploadScan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      apiClient.encounters.uploadScan(id, file),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.id),
      });
    },
  });
}
```

### Task 7.2: Notes, summaries, patients, and practice hooks

- [ ] **Step 1 (2 min):** Write failing tests for notes hooks.

File: `web/src/hooks/use-notes.test.ts`
```typescript
import { describe, it, expect } from "vitest";
import { useNote, useUpdateNote, useApproveNote } from "@/hooks/use-notes";

describe("Notes hooks", () => {
  it("exports all note hook functions", () => {
    expect(useNote).toBeInstanceOf(Function);
    expect(useUpdateNote).toBeInstanceOf(Function);
    expect(useApproveNote).toBeInstanceOf(Function);
  });
});
```

- [ ] **Step 2 (3 min):** Implement notes hooks.

File: `web/src/hooks/use-notes.ts`
```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { UpdateNoteRequest } from "@/types";
import { encounterKeys } from "@/hooks/use-encounters";

export const noteKeys = {
  detail: (encounterId: string) => ["notes", encounterId] as const,
};

export function useNote(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: noteKeys.detail(encounterId),
    queryFn: () => apiClient.notes.get(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useUpdateNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      encounterId,
      data,
    }: {
      encounterId: string;
      data: UpdateNoteRequest;
    }) => apiClient.notes.update(encounterId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: noteKeys.detail(variables.encounterId),
      });
    },
  });
}

export function useApproveNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (encounterId: string) => apiClient.notes.approve(encounterId),
    onSuccess: (_, encounterId) => {
      queryClient.invalidateQueries({
        queryKey: noteKeys.detail(encounterId),
      });
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(encounterId),
      });
    },
  });
}
```

- [ ] **Step 3 (3 min):** Implement summaries hooks.

File: `web/src/hooks/use-summaries.ts`
```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { SendSummaryRequest } from "@/types";
import { encounterKeys } from "@/hooks/use-encounters";

export const summaryKeys = {
  detail: (encounterId: string) => ["summaries", encounterId] as const,
};

export function useSummary(encounterId: string, enabled = true) {
  return useQuery({
    queryKey: summaryKeys.detail(encounterId),
    queryFn: () => apiClient.summaries.get(encounterId),
    enabled: !!encounterId && enabled,
  });
}

export function useSendSummary() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      encounterId,
      data,
    }: {
      encounterId: string;
      data: SendSummaryRequest;
    }) => apiClient.summaries.send(encounterId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: summaryKeys.detail(variables.encounterId),
      });
      queryClient.invalidateQueries({
        queryKey: encounterKeys.detail(variables.encounterId),
      });
    },
  });
}
```

- [ ] **Step 4 (3 min):** Implement patients hooks.

File: `web/src/hooks/use-patients.ts`
```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { CreatePatientRequest } from "@/types";

export const patientKeys = {
  all: ["patients"] as const,
  lists: () => [...patientKeys.all, "list"] as const,
  list: (params: Record<string, string>) =>
    [...patientKeys.lists(), params] as const,
  details: () => [...patientKeys.all, "detail"] as const,
  detail: (id: string) => [...patientKeys.details(), id] as const,
};

export function usePatients(params?: Record<string, string>) {
  return useQuery({
    queryKey: patientKeys.list(params || {}),
    queryFn: () => apiClient.patients.list(params),
  });
}

export function usePatient(id: string) {
  return useQuery({
    queryKey: patientKeys.detail(id),
    queryFn: () => apiClient.patients.get(id),
    enabled: !!id,
  });
}

export function useCreatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CreatePatientRequest) => apiClient.patients.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
    },
  });
}

export function useUpdatePatient() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<CreatePatientRequest>;
    }) => apiClient.patients.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: patientKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: patientKeys.lists() });
    },
  });
}
```

- [ ] **Step 5 (2 min):** Implement practice hooks.

File: `web/src/hooks/use-practice.ts`
```typescript
"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "@/lib/api-client";
import type { Practice } from "@/types";

export const practiceKeys = {
  detail: ["practice"] as const,
  stats: ["practice", "stats"] as const,
  auditLog: (params: Record<string, string>) =>
    ["practice", "audit-log", params] as const,
};

export function usePractice() {
  return useQuery({
    queryKey: practiceKeys.detail,
    queryFn: () => apiClient.practice.get(),
  });
}

export function usePracticeStats() {
  return useQuery({
    queryKey: practiceKeys.stats,
    queryFn: () => apiClient.practice.getStats(),
  });
}

export function useUpdatePractice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Practice>) => apiClient.practice.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: practiceKeys.detail });
    },
  });
}

export function useAuditLog(params?: Record<string, string>) {
  return useQuery({
    queryKey: practiceKeys.auditLog(params || {}),
    queryFn: () => apiClient.practice.getAuditLog(params),
  });
}
```

Run: `cd web && npm run test:run`
Verify: All tests pass.

---

## Chunk 8: Encounters List Page

### Task 8.1: Encounters list page with filtering

- [ ] **Step 1 (3 min):** Write failing tests for the encounters list.

File: `web/src/app/(dashboard)/encounters/encounters-list.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { EncountersList } from "./encounters-list";

vi.mock("@/hooks/use-encounters", () => ({
  useEncounters: () => ({
    data: {
      count: 2,
      results: [
        {
          id: "uuid-1",
          patient: "patient-1",
          encounter_date: "2026-03-15",
          input_method: "paste",
          status: "ready_for_review",
          created_at: "2026-03-15T10:00:00Z",
        },
        {
          id: "uuid-2",
          patient: "patient-2",
          encounter_date: "2026-03-14",
          input_method: "recording",
          status: "transcribing",
          created_at: "2026-03-14T14:00:00Z",
        },
      ],
    },
    isLoading: false,
    error: null,
  }),
}));

describe("EncountersList", () => {
  it("renders a heading", () => {
    render(<EncountersList />);
    expect(screen.getByText(/encounters/i)).toBeInTheDocument();
  });

  it("renders encounter rows", () => {
    render(<EncountersList />);
    expect(screen.getByText("Ready for Review")).toBeInTheDocument();
    expect(screen.getByText("Transcribing")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 (5 min):** Implement the encounters list component.

File: `web/src/components/shared/status-badge.tsx`
```typescript
import { Badge } from "@/components/ui/badge";
import { ENCOUNTER_STATUSES } from "@/lib/constants";
import type { EncounterStatus } from "@/types";
import { cn } from "@/lib/utils";

const statusVariants: Record<string, string> = {
  uploading: "bg-blue-100 text-blue-800",
  transcribing: "bg-yellow-100 text-yellow-800",
  generating_note: "bg-yellow-100 text-yellow-800",
  generating_summary: "bg-yellow-100 text-yellow-800",
  ready_for_review: "bg-orange-100 text-orange-800",
  approved: "bg-green-100 text-green-800",
  delivered: "bg-green-200 text-green-900",
  transcription_failed: "bg-red-100 text-red-800",
  note_generation_failed: "bg-red-100 text-red-800",
  summary_generation_failed: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: EncounterStatus }) {
  const label = ENCOUNTER_STATUSES[status] || status;
  return (
    <Badge variant="outline" className={cn("font-medium", statusVariants[status])}>
      {label}
    </Badge>
  );
}
```

File: `web/src/app/(dashboard)/encounters/encounters-list.tsx`
```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import { format } from "date-fns";
import { useEncounters } from "@/hooks/use-encounters";
import { StatusBadge } from "@/components/shared/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { PlusCircle, FileText, Mic, Camera, Keyboard } from "lucide-react";
import type { InputMethod } from "@/types";

const inputMethodIcons: Record<InputMethod, typeof FileText> = {
  paste: Keyboard,
  recording: Mic,
  dictation: FileText,
  scan: Camera,
};

export function EncountersList() {
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const params: Record<string, string> = {};
  if (statusFilter !== "all") params.status = statusFilter;

  const { data, isLoading, error } = useEncounters(params);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Encounters</h1>
        <Link href="/encounters/new">
          <Button>
            <PlusCircle className="mr-2 h-4 w-4" />
            New Encounter
          </Button>
        </Link>
      </div>

      <div className="flex gap-4">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Filter by status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="uploading">Uploading</SelectItem>
            <SelectItem value="transcribing">Transcribing</SelectItem>
            <SelectItem value="generating_note">Generating Note</SelectItem>
            <SelectItem value="generating_summary">Generating Summary</SelectItem>
            <SelectItem value="ready_for_review">Ready for Review</SelectItem>
            <SelectItem value="approved">Approved</SelectItem>
            <SelectItem value="delivered">Delivered</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center text-destructive">
            Failed to load encounters. Please try again.
          </CardContent>
        </Card>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <p className="text-muted-foreground">No encounters found.</p>
            <Link href="/encounters/new">
              <Button variant="outline" className="mt-4">
                <PlusCircle className="mr-2 h-4 w-4" />
                Create your first encounter
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-2">
          {data.results.map((encounter) => {
            const Icon = inputMethodIcons[encounter.input_method];
            return (
              <Link key={encounter.id} href={`/encounters/${encounter.id}`}>
                <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                  <CardContent className="flex items-center justify-between py-4">
                    <div className="flex items-center gap-4">
                      <Icon className="h-5 w-5 text-muted-foreground" />
                      <div>
                        <p className="font-medium">
                          {format(new Date(encounter.encounter_date), "MMM d, yyyy")}
                        </p>
                        <p className="text-sm text-muted-foreground capitalize">
                          {encounter.input_method}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={encounter.status} />
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      )}

      {data && data.count > 20 && (
        <div className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            Showing {data.results.length} of {data.count} encounters
          </p>
        </div>
      )}
    </div>
  );
}
```

File: `web/src/app/(dashboard)/encounters/page.tsx`
```typescript
import { EncountersList } from "./encounters-list";

export default function EncountersPage() {
  return <EncountersList />;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 9: New Encounter Page (Record/Paste/Dictate/Scan)

### Task 9.1: Audio recorder component

- [ ] **Step 1 (3 min):** Write failing tests for audio recorder.

File: `web/src/components/encounters/audio-recorder.test.tsx`
```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { AudioRecorder } from "@/components/encounters/audio-recorder";

describe("AudioRecorder", () => {
  it("renders start recording button", () => {
    render(<AudioRecorder onRecordingComplete={vi.fn()} />);
    expect(screen.getByRole("button", { name: /start recording/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2 (5 min):** Implement audio recorder using MediaRecorder + RecordRTC.

File: `web/src/components/encounters/audio-recorder.tsx`
```typescript
"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Mic, Square, Pause, Play } from "lucide-react";
import { MAX_RECORDING_DURATION_MS } from "@/lib/constants";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob, duration: number) => void;
  disabled?: boolean;
}

export function AudioRecorder({ onRecordingComplete, disabled }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [duration, setDuration] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>();
  const startTimeRef = useRef<number>(0);
  const elapsedRef = useRef<number>(0);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = useCallback(async () => {
    setError(null);
    chunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        stream.getTracks().forEach((track) => track.stop());
        if (timerRef.current) clearInterval(timerRef.current);
        const finalDuration = elapsedRef.current;
        onRecordingComplete(blob, finalDuration);
        setIsRecording(false);
        setIsPaused(false);
        setDuration(0);
        elapsedRef.current = 0;
      };

      recorder.start(1000); // Collect data every second
      setIsRecording(true);
      startTimeRef.current = Date.now();

      timerRef.current = setInterval(() => {
        const elapsed = elapsedRef.current + (Date.now() - startTimeRef.current);
        setDuration(Math.floor(elapsed / 1000));
        if (elapsed >= MAX_RECORDING_DURATION_MS) {
          stopRecording();
        }
      }, 500);
    } catch {
      setError("Microphone access denied. Please allow microphone access to record.");
    }
  }, [onRecordingComplete]);

  const stopRecording = useCallback(() => {
    elapsedRef.current += Date.now() - startTimeRef.current;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const togglePause = useCallback(() => {
    if (!mediaRecorderRef.current) return;
    if (isPaused) {
      mediaRecorderRef.current.resume();
      startTimeRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const elapsed = elapsedRef.current + (Date.now() - startTimeRef.current);
        setDuration(Math.floor(elapsed / 1000));
      }, 500);
      setIsPaused(false);
    } else {
      mediaRecorderRef.current.pause();
      elapsedRef.current += Date.now() - startTimeRef.current;
      if (timerRef.current) clearInterval(timerRef.current);
      setIsPaused(true);
    }
  }, [isPaused]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-8">
        {error && <p className="text-sm text-destructive">{error}</p>}

        {isRecording && (
          <div className="text-center">
            <div className="flex items-center gap-2 mb-2">
              <div className={`h-3 w-3 rounded-full ${isPaused ? "bg-yellow-500" : "bg-red-500 animate-pulse"}`} />
              <span className="text-sm font-medium">{isPaused ? "Paused" : "Recording"}</span>
            </div>
            <p className="text-3xl font-mono font-bold">{formatDuration(duration)}</p>
          </div>
        )}

        <div className="flex gap-3">
          {!isRecording ? (
            <Button onClick={startRecording} disabled={disabled} size="lg">
              <Mic className="mr-2 h-5 w-5" />
              Start Recording
            </Button>
          ) : (
            <>
              <Button onClick={togglePause} variant="outline" size="lg">
                {isPaused ? <Play className="mr-2 h-5 w-5" /> : <Pause className="mr-2 h-5 w-5" />}
                {isPaused ? "Resume" : "Pause"}
              </Button>
              <Button onClick={stopRecording} variant="destructive" size="lg">
                <Square className="mr-2 h-5 w-5" />
                Stop
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 9.2: Paste input, scan upload, and new encounter page

- [ ] **Step 1 (3 min):** Implement paste input component.

File: `web/src/components/encounters/paste-input.tsx`
```typescript
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { MAX_PASTE_LENGTH } from "@/lib/constants";

const pasteSchema = z.object({
  text: z
    .string()
    .min(10, "Text must be at least 10 characters")
    .max(MAX_PASTE_LENGTH, `Text must be under ${MAX_PASTE_LENGTH.toLocaleString()} characters`),
});

type PasteFormData = z.infer<typeof pasteSchema>;

interface PasteInputProps {
  onSubmit: (text: string) => void;
  isSubmitting?: boolean;
}

export function PasteInput({ onSubmit, isSubmitting }: PasteInputProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<PasteFormData>({
    resolver: zodResolver(pasteSchema),
  });

  const textValue = watch("text", "");

  return (
    <Card>
      <CardContent className="py-6">
        <form onSubmit={handleSubmit((data) => onSubmit(data.text))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="paste-text">Paste Clinical Notes</Label>
            <Textarea
              id="paste-text"
              placeholder="Paste your clinical notes here..."
              className="min-h-[200px] font-mono text-sm"
              {...register("text")}
            />
            <div className="flex justify-between">
              {errors.text && (
                <p className="text-sm text-destructive">{errors.text.message}</p>
              )}
              <p className="text-sm text-muted-foreground ml-auto">
                {textValue.length.toLocaleString()} / {MAX_PASTE_LENGTH.toLocaleString()}
              </p>
            </div>
          </div>
          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? "Submitting..." : "Submit Notes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 2 (3 min):** Implement scan upload component.

File: `web/src/components/encounters/scan-upload.tsx`
```typescript
"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Camera, Upload, X } from "lucide-react";

interface ScanUploadProps {
  onUpload: (file: File) => void;
  isUploading?: boolean;
}

export function ScanUpload({ onUpload, isUploading }: ScanUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      return;
    }
    setSelectedFile(file);
    const reader = new FileReader();
    reader.onloadend = () => setPreview(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleUpload = () => {
    if (selectedFile) onUpload(selectedFile);
  };

  const clearSelection = () => {
    setPreview(null);
    setSelectedFile(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <Card>
      <CardContent className="py-6 space-y-4">
        {!preview ? (
          <div
            className="border-2 border-dashed rounded-lg p-12 text-center cursor-pointer hover:border-primary transition-colors"
            onClick={() => inputRef.current?.click()}
          >
            <Camera className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="font-medium">Upload a scanned document or photo</p>
            <p className="text-sm text-muted-foreground mt-1">
              Supports JPG, PNG, PDF. Max 10MB.
            </p>
            <input
              ref={inputRef}
              type="file"
              accept="image/*,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        ) : (
          <div className="space-y-4">
            <div className="relative">
              <img src={preview} alt="Scan preview" className="max-h-64 mx-auto rounded-lg" />
              <Button
                variant="destructive"
                size="icon"
                className="absolute top-2 right-2"
                onClick={clearSelection}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <Button onClick={handleUpload} disabled={isUploading} className="w-full">
              <Upload className="mr-2 h-4 w-4" />
              {isUploading ? "Processing..." : "Process Scan"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 3 (5 min):** Implement the new encounter page (orchestrates all input methods).

File: `web/src/app/(dashboard)/encounters/new/new-encounter-form.tsx`
```typescript
"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { format } from "date-fns";
import {
  useCreateEncounter,
  usePasteInput,
  useUploadRecording,
  useUploadScan,
  useDictationInput,
} from "@/hooks/use-encounters";
import { usePatients } from "@/hooks/use-patients";
import { AudioRecorder } from "@/components/encounters/audio-recorder";
import { PasteInput } from "@/components/encounters/paste-input";
import { ScanUpload } from "@/components/encounters/scan-upload";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import type { InputMethod } from "@/types";

const encounterSchema = z.object({
  patient: z.string().min(1, "Patient is required"),
  encounter_date: z.string().min(1, "Date is required"),
  consent_recording: z.boolean().default(false),
  consent_method: z.string().optional(),
  consent_jurisdiction_state: z.string().optional(),
});

type EncounterFormData = z.infer<typeof encounterSchema>;

export function NewEncounterForm() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<InputMethod>("paste");
  const [encounterId, setEncounterId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: patientsData } = usePatients();
  const createEncounter = useCreateEncounter();
  const pasteInput = usePasteInput();
  const uploadRecording = useUploadRecording();
  const uploadScan = useUploadScan();
  const dictationInput = useDictationInput();

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<EncounterFormData>({
    resolver: zodResolver(encounterSchema),
    defaultValues: {
      encounter_date: format(new Date(), "yyyy-MM-dd"),
      consent_recording: false,
    },
  });

  const createAndProcess = async (
    formData: EncounterFormData,
    inputMethod: InputMethod,
    processInput: (encounterId: string) => Promise<void>
  ) => {
    setError(null);
    try {
      const encounter = await createEncounter.mutateAsync({
        patient: formData.patient,
        encounter_date: formData.encounter_date,
        input_method: inputMethod,
        consent_recording: formData.consent_recording,
        consent_method: formData.consent_method,
        consent_jurisdiction_state: formData.consent_jurisdiction_state,
      });
      setEncounterId(encounter.id);
      await processInput(encounter.id);
      router.push(`/encounters/${encounter.id}`);
    } catch {
      setError("Failed to create encounter. Please try again.");
    }
  };

  const handlePasteSubmit = (text: string) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "paste", (id) =>
        pasteInput.mutateAsync({ id, text })
      )
    )();
  };

  const handleRecordingComplete = (blob: Blob, duration: number) => {
    const file = new File([blob], `recording-${Date.now()}.webm`, {
      type: blob.type,
    });
    handleSubmit((formData) =>
      createAndProcess(formData, "recording", (id) =>
        uploadRecording.mutateAsync({ id, file })
      )
    )();
  };

  const handleScanUpload = (file: File) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "scan", (id) =>
        uploadScan.mutateAsync({ id, file })
      )
    )();
  };

  const handleDictation = (text: string) => {
    handleSubmit((formData) =>
      createAndProcess(formData, "dictation", (id) =>
        dictationInput.mutateAsync({ id, text })
      )
    )();
  };

  const isProcessing =
    createEncounter.isPending ||
    pasteInput.isPending ||
    uploadRecording.isPending ||
    uploadScan.isPending ||
    dictationInput.isPending;

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">New Encounter</h1>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Encounter Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="patient">Patient</Label>
              <Select onValueChange={(value) => setValue("patient", value)}>
                <SelectTrigger>
                  <SelectValue placeholder="Select patient" />
                </SelectTrigger>
                <SelectContent>
                  {patientsData?.results.map((patient) => (
                    <SelectItem key={patient.id} value={patient.id}>
                      {patient.first_name} {patient.last_name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.patient && (
                <p className="text-sm text-destructive">{errors.patient.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="encounter_date">Date</Label>
              <Input type="date" {...register("encounter_date")} />
              {errors.encounter_date && (
                <p className="text-sm text-destructive">
                  {errors.encounter_date.message}
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Input Method</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as InputMethod)}
          >
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="paste">Paste</TabsTrigger>
              <TabsTrigger value="recording">Record</TabsTrigger>
              <TabsTrigger value="dictation">Dictate</TabsTrigger>
              <TabsTrigger value="scan">Scan</TabsTrigger>
            </TabsList>

            <TabsContent value="paste" className="mt-4">
              <PasteInput
                onSubmit={handlePasteSubmit}
                isSubmitting={isProcessing}
              />
            </TabsContent>

            <TabsContent value="recording" className="mt-4">
              <AudioRecorder
                onRecordingComplete={handleRecordingComplete}
                disabled={isProcessing}
              />
            </TabsContent>

            <TabsContent value="dictation" className="mt-4">
              <Card>
                <CardContent className="py-6">
                  <DictationInput
                    onSubmit={handleDictation}
                    isSubmitting={isProcessing}
                  />
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="scan" className="mt-4">
              <ScanUpload
                onUpload={handleScanUpload}
                isUploading={isProcessing}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}

function DictationInput({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (text: string) => void;
  isSubmitting?: boolean;
}) {
  const [text, setText] = useState("");
  return (
    <div className="space-y-4">
      <Label htmlFor="dictation">Dictate Clinical Notes</Label>
      <Textarea
        id="dictation"
        placeholder="Dictate or type your clinical notes..."
        className="min-h-[200px]"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <Button
        onClick={() => onSubmit(text)}
        disabled={isSubmitting || text.length < 10}
        className="w-full"
      >
        {isSubmitting ? "Submitting..." : "Submit Dictation"}
      </Button>
    </div>
  );
}
```

File: `web/src/app/(dashboard)/encounters/new/page.tsx`
```typescript
import { NewEncounterForm } from "./new-encounter-form";

export default function NewEncounterPage() {
  return <NewEncounterForm />;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 10: Encounter Detail Page (Review Outputs)

### Task 10.1: Processing status component

- [ ] **Step 1 (3 min):** Write failing tests and implement processing status display.

File: `web/src/components/encounters/processing-status.test.tsx`
```typescript
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
```

- [ ] **Step 2 (4 min):** Implement processing status component with WebSocket integration.

File: `web/src/components/encounters/processing-status.tsx`
```typescript
"use client";

import { useEffect } from "react";
import { useJobStatus } from "@/hooks/use-job-status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { CheckCircle2, Loader2, XCircle, Circle } from "lucide-react";
import type { EncounterStatus } from "@/types";

interface ProcessingStatusProps {
  encounterId: string;
  currentStatus: EncounterStatus;
  onStatusChange?: (status: EncounterStatus) => void;
}

const steps: { key: EncounterStatus; label: string }[] = [
  { key: "uploading", label: "Uploading" },
  { key: "transcribing", label: "Transcribing Audio" },
  { key: "generating_note", label: "Generating SOAP Note" },
  { key: "generating_summary", label: "Generating Summary" },
  { key: "ready_for_review", label: "Ready for Review" },
];

const statusOrder: EncounterStatus[] = [
  "uploading",
  "transcribing",
  "generating_note",
  "generating_summary",
  "ready_for_review",
];

const failedStatuses: EncounterStatus[] = [
  "transcription_failed",
  "note_generation_failed",
  "summary_generation_failed",
];

export function ProcessingStatus({
  encounterId,
  currentStatus,
  onStatusChange,
}: ProcessingStatusProps) {
  const isProcessing =
    !failedStatuses.includes(currentStatus) &&
    currentStatus !== "ready_for_review" &&
    currentStatus !== "approved" &&
    currentStatus !== "delivered";

  const { status: wsStatus } = useJobStatus(encounterId, {
    enabled: isProcessing,
    onStatusChange,
  });

  const activeStatus = wsStatus || currentStatus;
  const currentIndex = statusOrder.indexOf(activeStatus);
  const isFailed = failedStatuses.includes(activeStatus);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Processing Status</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {steps.map((step, index) => {
            const isComplete = currentIndex > index;
            const isActive = currentIndex === index;
            const isFailedAtStep = isFailed && currentIndex === index;

            return (
              <div key={step.key} className="flex items-center gap-3">
                {isComplete ? (
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                ) : isFailedAtStep ? (
                  <XCircle className="h-5 w-5 text-red-600" />
                ) : isActive ? (
                  <Loader2 className="h-5 w-5 text-primary animate-spin" />
                ) : (
                  <Circle className="h-5 w-5 text-muted-foreground/40" />
                )}
                <span
                  className={cn(
                    "text-sm",
                    isComplete && "text-green-700 font-medium",
                    isActive && !isFailedAtStep && "text-primary font-medium",
                    isFailedAtStep && "text-red-700 font-medium",
                    !isComplete && !isActive && "text-muted-foreground"
                  )}
                >
                  {step.label}
                  {isFailedAtStep && " - Failed"}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 10.2: SOAP note editor component

- [ ] **Step 1 (4 min):** Implement SOAP note editor.

File: `web/src/components/notes/note-editor.tsx`
```typescript
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useUpdateNote, useApproveNote } from "@/hooks/use-notes";
import type { ClinicalNote } from "@/types";
import { CheckCircle2, Edit3, Save } from "lucide-react";
import { useState } from "react";

const noteSchema = z.object({
  subjective: z.string().min(1, "Subjective is required"),
  objective: z.string().min(1, "Objective is required"),
  assessment: z.string().min(1, "Assessment is required"),
  plan: z.string().min(1, "Plan is required"),
});

type NoteFormData = z.infer<typeof noteSchema>;

interface NoteEditorProps {
  note: ClinicalNote;
  encounterId: string;
  onApproved?: () => void;
}

export function NoteEditor({ note, encounterId, onApproved }: NoteEditorProps) {
  const [isEditing, setIsEditing] = useState(false);
  const updateNote = useUpdateNote();
  const approveNote = useApproveNote();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<NoteFormData>({
    resolver: zodResolver(noteSchema),
    defaultValues: {
      subjective: note.subjective,
      objective: note.objective,
      assessment: note.assessment,
      plan: note.plan,
    },
  });

  const onSave = async (data: NoteFormData) => {
    await updateNote.mutateAsync({
      encounterId,
      data: { ...data, doctor_edited: true },
    });
    setIsEditing(false);
  };

  const onApprove = async () => {
    await approveNote.mutateAsync(encounterId);
    onApproved?.();
  };

  const isApproved = !!note.approved_at;

  const soapSections = [
    { key: "subjective" as const, label: "Subjective", field: "subjective" as const },
    { key: "objective" as const, label: "Objective", field: "objective" as const },
    { key: "assessment" as const, label: "Assessment", field: "assessment" as const },
    { key: "plan" as const, label: "Plan", field: "plan" as const },
  ];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="text-lg">SOAP Note</CardTitle>
          <div className="flex gap-2">
            {note.ai_generated && <Badge variant="secondary">AI Generated</Badge>}
            {note.doctor_edited && <Badge variant="outline">Doctor Edited</Badge>}
            {isApproved && <Badge className="bg-green-100 text-green-800">Approved</Badge>}
          </div>
        </div>
        {!isApproved && (
          <div className="flex gap-2">
            {!isEditing ? (
              <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
                <Edit3 className="mr-2 h-4 w-4" />
                Edit
              </Button>
            ) : (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  reset();
                  setIsEditing(false);
                }}
              >
                Cancel
              </Button>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSave)} className="space-y-4">
          {soapSections.map((section) => (
            <div key={section.key} className="space-y-2">
              <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {section.label}
              </Label>
              {isEditing ? (
                <>
                  <Textarea
                    className="min-h-[80px]"
                    {...register(section.field)}
                  />
                  {errors[section.field] && (
                    <p className="text-sm text-destructive">
                      {errors[section.field]?.message}
                    </p>
                  )}
                </>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{note[section.field]}</p>
              )}
              <Separator />
            </div>
          ))}

          {(note.icd10_codes.length > 0 || note.cpt_codes.length > 0) && (
            <div className="flex gap-8">
              {note.icd10_codes.length > 0 && (
                <div>
                  <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    ICD-10 Codes
                  </Label>
                  <div className="flex gap-1 mt-1">
                    {note.icd10_codes.map((code) => (
                      <Badge key={code} variant="outline">{code}</Badge>
                    ))}
                  </div>
                </div>
              )}
              {note.cpt_codes.length > 0 && (
                <div>
                  <Label className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                    CPT Codes
                  </Label>
                  <div className="flex gap-1 mt-1">
                    {note.cpt_codes.map((code) => (
                      <Badge key={code} variant="outline">{code}</Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {isEditing && isDirty && (
            <Button type="submit" disabled={updateNote.isPending}>
              <Save className="mr-2 h-4 w-4" />
              {updateNote.isPending ? "Saving..." : "Save Changes"}
            </Button>
          )}
        </form>

        {!isApproved && !isEditing && (
          <div className="mt-6 pt-4 border-t">
            <Button
              onClick={onApprove}
              disabled={approveNote.isPending}
              className="w-full"
              size="lg"
            >
              <CheckCircle2 className="mr-2 h-5 w-5" />
              {approveNote.isPending ? "Approving..." : "Approve Note"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Task 10.3: Summary preview and send component

- [ ] **Step 1 (4 min):** Implement summary preview.

File: `web/src/components/encounters/summary-preview.tsx`
```typescript
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useSendSummary } from "@/hooks/use-summaries";
import type { PatientSummary, DeliveryMethod } from "@/types";
import { Send, Eye, Languages } from "lucide-react";

interface SummaryPreviewProps {
  summary: PatientSummary;
  encounterId: string;
  onSent?: () => void;
}

export function SummaryPreview({
  summary,
  encounterId,
  onSent,
}: SummaryPreviewProps) {
  const [deliveryMethod, setDeliveryMethod] = useState<DeliveryMethod>("app");
  const sendSummary = useSendSummary();

  const handleSend = async () => {
    await sendSummary.mutateAsync({
      encounterId,
      data: { delivery_method: deliveryMethod },
    });
    onSent?.();
  };

  const isSent = summary.delivery_status !== "pending";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-1">
          <CardTitle className="text-lg">Patient Summary</CardTitle>
          <div className="flex gap-2">
            <Badge variant="outline" className="capitalize">
              {summary.reading_level.replace("_", " ")}
            </Badge>
            <Badge
              variant={isSent ? "default" : "secondary"}
              className={isSent ? "bg-green-100 text-green-800" : ""}
            >
              {summary.delivery_status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Tabs defaultValue="en">
          <TabsList>
            <TabsTrigger value="en">
              <Languages className="mr-2 h-4 w-4" />
              English
            </TabsTrigger>
            {summary.summary_es && (
              <TabsTrigger value="es">
                <Languages className="mr-2 h-4 w-4" />
                Spanish
              </TabsTrigger>
            )}
          </TabsList>
          <TabsContent value="en" className="mt-4">
            <div className="prose prose-sm max-w-none">
              <p className="whitespace-pre-wrap">{summary.summary_en}</p>
            </div>
          </TabsContent>
          {summary.summary_es && (
            <TabsContent value="es" className="mt-4">
              <div className="prose prose-sm max-w-none">
                <p className="whitespace-pre-wrap">{summary.summary_es}</p>
              </div>
            </TabsContent>
          )}
        </Tabs>

        {summary.medical_terms_explained.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold mb-2">Medical Terms Explained</h4>
            <div className="space-y-2">
              {summary.medical_terms_explained.map((term, idx) => (
                <div key={idx} className="text-sm">
                  <span className="font-medium">{term.term}:</span>{" "}
                  <span className="text-muted-foreground">{term.explanation}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="text-xs text-muted-foreground italic border-t pt-3">
          {summary.disclaimer_text}
        </div>

        {!isSent && (
          <div className="flex gap-3 pt-4 border-t">
            <Select
              value={deliveryMethod}
              onValueChange={(v) => setDeliveryMethod(v as DeliveryMethod)}
            >
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="app">Mobile App</SelectItem>
                <SelectItem value="sms_link">SMS Link</SelectItem>
                <SelectItem value="email_link">Email Link</SelectItem>
                <SelectItem value="widget">Clinic Widget</SelectItem>
              </SelectContent>
            </Select>
            <Button
              onClick={handleSend}
              disabled={sendSummary.isPending}
              className="flex-1"
            >
              <Send className="mr-2 h-4 w-4" />
              {sendSummary.isPending ? "Sending..." : "Send to Patient"}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### Task 10.4: Encounter detail page (orchestrates all output panels)

- [ ] **Step 1 (5 min):** Implement the encounter detail page.

File: `web/src/app/(dashboard)/encounters/[id]/encounter-detail.tsx`
```typescript
"use client";

import { useEncounter, useTranscript } from "@/hooks/use-encounters";
import { useNote } from "@/hooks/use-notes";
import { useSummary } from "@/hooks/use-summaries";
import { useQueryClient } from "@tanstack/react-query";
import { encounterKeys } from "@/hooks/use-encounters";
import { ProcessingStatus } from "@/components/encounters/processing-status";
import { NoteEditor } from "@/components/notes/note-editor";
import { SummaryPreview } from "@/components/encounters/summary-preview";
import { StatusBadge } from "@/components/shared/status-badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";
import type { EncounterStatus } from "@/types";

interface EncounterDetailProps {
  encounterId: string;
}

const completedStatuses: EncounterStatus[] = [
  "ready_for_review",
  "approved",
  "delivered",
];

const failedStatuses: EncounterStatus[] = [
  "transcription_failed",
  "note_generation_failed",
  "summary_generation_failed",
];

export function EncounterDetail({ encounterId }: EncounterDetailProps) {
  const queryClient = useQueryClient();

  const { data: encounter, isLoading: encounterLoading } =
    useEncounter(encounterId);

  const showOutputs =
    encounter && completedStatuses.includes(encounter.status);
  const showProcessing =
    encounter &&
    !completedStatuses.includes(encounter.status) &&
    !failedStatuses.includes(encounter.status);
  const showFailed =
    encounter && failedStatuses.includes(encounter.status);

  const { data: transcript } = useTranscript(
    encounterId,
    !!encounter?.has_transcript || showOutputs === true
  );
  const { data: note } = useNote(
    encounterId,
    !!encounter?.has_note || showOutputs === true
  );
  const { data: summary } = useSummary(
    encounterId,
    !!encounter?.has_summary || showOutputs === true
  );

  const handleStatusChange = (status: EncounterStatus) => {
    queryClient.invalidateQueries({
      queryKey: encounterKeys.detail(encounterId),
    });
  };

  if (encounterLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!encounter) {
    return (
      <Card>
        <CardContent className="py-12 text-center">
          <p className="text-muted-foreground">Encounter not found.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/encounters">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">
            Encounter - {format(new Date(encounter.encounter_date), "MMMM d, yyyy")}
          </h1>
          <p className="text-sm text-muted-foreground capitalize">
            Input: {encounter.input_method}
          </p>
        </div>
        <StatusBadge status={encounter.status} />
      </div>

      {showProcessing && (
        <ProcessingStatus
          encounterId={encounterId}
          currentStatus={encounter.status}
          onStatusChange={handleStatusChange}
        />
      )}

      {showFailed && (
        <Card className="border-destructive">
          <CardContent className="py-6 text-center">
            <p className="text-destructive font-medium">
              Processing failed at: {encounter.status.replace(/_/g, " ")}
            </p>
            <Button variant="outline" className="mt-4" onClick={() =>
              queryClient.invalidateQueries({ queryKey: encounterKeys.detail(encounterId) })
            }>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {transcript && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Transcript</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto">
              {transcript.speaker_segments.length > 0 ? (
                <div className="space-y-2">
                  {transcript.speaker_segments.map((seg, idx) => (
                    <div key={idx} className="text-sm">
                      <span className="font-medium capitalize">{seg.speaker}:</span>{" "}
                      <span>{seg.text}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm whitespace-pre-wrap">{transcript.raw_text}</p>
              )}
            </div>
            {transcript.confidence_score > 0 && (
              <p className="text-xs text-muted-foreground mt-2">
                Confidence: {(transcript.confidence_score * 100).toFixed(0)}%
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {note && (
        <NoteEditor
          note={note}
          encounterId={encounterId}
          onApproved={() =>
            queryClient.invalidateQueries({
              queryKey: encounterKeys.detail(encounterId),
            })
          }
        />
      )}

      {summary && (
        <SummaryPreview
          summary={summary}
          encounterId={encounterId}
          onSent={() =>
            queryClient.invalidateQueries({
              queryKey: encounterKeys.detail(encounterId),
            })
          }
        />
      )}
    </div>
  );
}
```

File: `web/src/app/(dashboard)/encounters/[id]/page.tsx`
```typescript
import { EncounterDetail } from "./encounter-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function EncounterDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <EncounterDetail encounterId={id} />;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 11: Patient Management Pages

### Task 11.1: Patients list page

- [ ] **Step 1 (4 min):** Implement patients list page.

File: `web/src/app/(dashboard)/patients/patients-list.tsx`
```typescript
"use client";

import { useState } from "react";
import Link from "next/link";
import { usePatients } from "@/hooks/use-patients";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { PlusCircle, Search } from "lucide-react";
import { CreatePatientForm } from "@/components/patients/create-patient-form";

export function PatientsList() {
  const [search, setSearch] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const params: Record<string, string> = {};
  if (search) params.name = search;

  const { data, isLoading } = usePatients(params);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Patients</h1>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <PlusCircle className="mr-2 h-4 w-4" />
              Add Patient
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add New Patient</DialogTitle>
            </DialogHeader>
            <CreatePatientForm onSuccess={() => setDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search patients by name..."
          className="pl-10"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </div>
      )}

      {data && data.results.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            No patients found.
          </CardContent>
        </Card>
      )}

      {data && data.results.length > 0 && (
        <div className="space-y-2">
          {data.results.map((patient) => (
            <Link key={patient.id} href={`/patients/${patient.id}`}>
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardContent className="flex items-center justify-between py-4">
                  <div>
                    <p className="font-medium">
                      {patient.first_name} {patient.last_name}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Language: {patient.language_preference.toUpperCase()}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
```

File: `web/src/app/(dashboard)/patients/page.tsx`
```typescript
import { PatientsList } from "./patients-list";

export default function PatientsPage() {
  return <PatientsList />;
}
```

### Task 11.2: Create patient form

- [ ] **Step 1 (4 min):** Implement create patient form.

File: `web/src/components/patients/create-patient-form.tsx`
```typescript
"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useCreatePatient } from "@/hooks/use-patients";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useState } from "react";

const createPatientSchema = z.object({
  first_name: z.string().min(1, "First name is required"),
  last_name: z.string().min(1, "Last name is required"),
  date_of_birth: z.string().min(1, "Date of birth is required"),
  email: z.string().email("Invalid email").optional().or(z.literal("")),
  phone: z.string().optional().or(z.literal("")),
  language_preference: z.string().default("en"),
});

type CreatePatientFormData = z.infer<typeof createPatientSchema>;

interface CreatePatientFormProps {
  onSuccess?: () => void;
}

export function CreatePatientForm({ onSuccess }: CreatePatientFormProps) {
  const createPatient = useCreatePatient();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<CreatePatientFormData>({
    resolver: zodResolver(createPatientSchema),
    defaultValues: { language_preference: "en" },
  });

  const onSubmit = async (data: CreatePatientFormData) => {
    setError(null);
    try {
      await createPatient.mutateAsync(data);
      onSuccess?.();
    } catch {
      setError("Failed to create patient. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name</Label>
          <Input id="first_name" {...register("first_name")} />
          {errors.first_name && (
            <p className="text-sm text-destructive">{errors.first_name.message}</p>
          )}
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name</Label>
          <Input id="last_name" {...register("last_name")} />
          {errors.last_name && (
            <p className="text-sm text-destructive">{errors.last_name.message}</p>
          )}
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="date_of_birth">Date of Birth</Label>
        <Input id="date_of_birth" type="date" {...register("date_of_birth")} />
        {errors.date_of_birth && (
          <p className="text-sm text-destructive">{errors.date_of_birth.message}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="patient-email">Email (optional)</Label>
        <Input id="patient-email" type="email" {...register("email")} />
      </div>
      <div className="space-y-2">
        <Label htmlFor="patient-phone">Phone (optional)</Label>
        <Input id="patient-phone" type="tel" placeholder="+15551234567" {...register("phone")} />
      </div>
      <div className="space-y-2">
        <Label>Language Preference</Label>
        <Select defaultValue="en" onValueChange={(v) => setValue("language_preference", v)}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="en">English</SelectItem>
            <SelectItem value="es">Spanish</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" className="w-full" disabled={createPatient.isPending}>
        {createPatient.isPending ? "Creating..." : "Add Patient"}
      </Button>
    </form>
  );
}
```

### Task 11.3: Patient detail page

- [ ] **Step 1 (3 min):** Implement patient detail page.

File: `web/src/app/(dashboard)/patients/[id]/patient-detail.tsx`
```typescript
"use client";

import { usePatient, useUpdatePatient } from "@/hooks/use-patients";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { format } from "date-fns";

interface PatientDetailProps {
  patientId: string;
}

export function PatientDetail({ patientId }: PatientDetailProps) {
  const { data: patient, isLoading } = usePatient(patientId);

  if (isLoading) {
    return <Skeleton className="h-64 w-full" />;
  }

  if (!patient) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          Patient not found.
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center gap-4">
        <Link href="/patients">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <h1 className="text-2xl font-bold">
          {patient.first_name} {patient.last_name}
        </h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Patient Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Date of Birth</p>
              <p className="font-medium">
                {format(new Date(patient.date_of_birth), "MMMM d, yyyy")}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Language</p>
              <p className="font-medium">{patient.language_preference.toUpperCase()}</p>
            </div>
            {patient.email && (
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{patient.email}</p>
              </div>
            )}
            {patient.phone && (
              <div>
                <p className="text-muted-foreground">Phone</p>
                <p className="font-medium">{patient.phone}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
```

File: `web/src/app/(dashboard)/patients/[id]/page.tsx`
```typescript
import { PatientDetail } from "./patient-detail";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PatientDetailPage({ params }: PageProps) {
  const { id } = await params;
  return <PatientDetail patientId={id} />;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 12: Practice Settings Page

### Task 12.1: Settings page with practice info and stats

- [ ] **Step 1 (4 min):** Implement settings page.

File: `web/src/app/(dashboard)/settings/settings-page.tsx`
```typescript
"use client";

import { usePractice, usePracticeStats, useUpdatePractice } from "@/hooks/use-practice";
import { useAuth } from "@/lib/auth-context";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";

export function SettingsPage() {
  const { user } = useAuth();
  const { data: practice, isLoading: practiceLoading } = usePractice();
  const { data: stats, isLoading: statsLoading } = usePracticeStats();
  const updatePractice = useUpdatePractice();

  const [practiceName, setPracticeName] = useState("");
  const [practicePhone, setPracticePhone] = useState("");

  const handleSave = async () => {
    const data: Record<string, string> = {};
    if (practiceName) data.name = practiceName;
    if (practicePhone) data.phone = practicePhone;
    if (Object.keys(data).length > 0) {
      await updatePractice.mutateAsync(data);
    }
  };

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">Practice Settings</h1>

      <Card>
        <CardHeader>
          <CardTitle>Your Profile</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-muted-foreground">Name</p>
              <p className="font-medium">{user?.first_name} {user?.last_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Email</p>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Specialty</p>
              <p className="font-medium">{user?.specialty || "Not set"}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Role</p>
              <Badge variant="outline" className="capitalize">{user?.role}</Badge>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Practice Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {practiceLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : practice ? (
            <>
              <div className="space-y-2">
                <Label>Practice Name</Label>
                <Input
                  defaultValue={practice.name}
                  onChange={(e) => setPracticeName(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  defaultValue={practice.phone}
                  onChange={(e) => setPracticePhone(e.target.value)}
                />
              </div>
              <div className="text-sm">
                <span className="text-muted-foreground">Subscription: </span>
                <Badge variant="outline" className="capitalize">
                  {practice.subscription_tier}
                </Badge>
              </div>
              <Button onClick={handleSave} disabled={updatePractice.isPending}>
                {updatePractice.isPending ? "Saving..." : "Save Changes"}
              </Button>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Dashboard Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          {statsLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : stats ? (
            <div className="grid grid-cols-2 gap-6">
              <div className="text-center p-4 border rounded-lg">
                <p className="text-3xl font-bold">{stats.total_patients}</p>
                <p className="text-sm text-muted-foreground">Total Patients</p>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <p className="text-3xl font-bold">{stats.total_encounters}</p>
                <p className="text-sm text-muted-foreground">Total Encounters</p>
              </div>
              {Object.entries(stats.encounters_by_status).map(([status, count]) => (
                <div key={status} className="text-center p-4 border rounded-lg">
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-sm text-muted-foreground capitalize">
                    {status.replace(/_/g, " ")}
                  </p>
                </div>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
```

File: `web/src/app/(dashboard)/settings/page.tsx`
```typescript
import { SettingsPage } from "./settings-page";

export default function SettingsRoute() {
  return <SettingsPage />;
}
```

Run: `cd web && npm run test:run`
Verify: Tests pass.

---

## Chunk 13: i18n Structure and Root Redirect

### Task 13.1: i18n setup with next-intl

- [ ] **Step 1 (3 min):** Create message files and i18n config.

File: `web/src/i18n/messages/en.json`
```json
{
  "common": {
    "appName": "MedicalNote",
    "loading": "Loading...",
    "save": "Save",
    "cancel": "Cancel",
    "delete": "Delete",
    "edit": "Edit",
    "back": "Back",
    "next": "Next",
    "submit": "Submit",
    "search": "Search",
    "noResults": "No results found"
  },
  "auth": {
    "signIn": "Sign In",
    "signOut": "Sign Out",
    "createAccount": "Create Account",
    "email": "Email",
    "password": "Password",
    "forgotPassword": "Forgot Password?"
  },
  "encounters": {
    "title": "Encounters",
    "newEncounter": "New Encounter",
    "paste": "Paste",
    "record": "Record",
    "dictate": "Dictate",
    "scan": "Scan",
    "approve": "Approve Note",
    "sendToPatient": "Send to Patient"
  },
  "patients": {
    "title": "Patients",
    "addPatient": "Add Patient",
    "firstName": "First Name",
    "lastName": "Last Name",
    "dateOfBirth": "Date of Birth"
  },
  "settings": {
    "title": "Practice Settings",
    "practiceInfo": "Practice Information",
    "profile": "Your Profile"
  }
}
```

File: `web/src/i18n/messages/es.json`
```json
{
  "common": {
    "appName": "MedicalNote",
    "loading": "Cargando...",
    "save": "Guardar",
    "cancel": "Cancelar",
    "delete": "Eliminar",
    "edit": "Editar",
    "back": "Volver",
    "next": "Siguiente",
    "submit": "Enviar",
    "search": "Buscar",
    "noResults": "No se encontraron resultados"
  },
  "auth": {
    "signIn": "Iniciar Sesion",
    "signOut": "Cerrar Sesion",
    "createAccount": "Crear Cuenta",
    "email": "Correo Electronico",
    "password": "Contrasena",
    "forgotPassword": "Olvidaste tu contrasena?"
  },
  "encounters": {
    "title": "Consultas",
    "newEncounter": "Nueva Consulta",
    "paste": "Pegar",
    "record": "Grabar",
    "dictate": "Dictar",
    "scan": "Escanear",
    "approve": "Aprobar Nota",
    "sendToPatient": "Enviar al Paciente"
  },
  "patients": {
    "title": "Pacientes",
    "addPatient": "Agregar Paciente",
    "firstName": "Nombre",
    "lastName": "Apellido",
    "dateOfBirth": "Fecha de Nacimiento"
  },
  "settings": {
    "title": "Configuracion de Practica",
    "practiceInfo": "Informacion de Practica",
    "profile": "Tu Perfil"
  }
}
```

File: `web/src/i18n/config.ts`
```typescript
export const locales = ["en", "es"] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = "en";
```

### Task 13.2: Root page redirect and cn utility

- [ ] **Step 1 (2 min):** Create root page redirect and utility.

File: `web/src/app/page.tsx`
```typescript
import { redirect } from "next/navigation";

export default function Home() {
  redirect("/encounters");
}
```

File: `web/src/lib/utils.ts`
```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Run: `cd web && npm run test:run && npm run build`
Verify: All tests pass and build succeeds.

---

## Chunk 14: MSW Mocks and Integration Tests

### Task 14.1: MSW handlers for API mocking in tests

- [ ] **Step 1 (4 min):** Create MSW handlers matching all backend endpoints.

File: `web/src/test/mocks/handlers.ts`
```typescript
import { http, HttpResponse } from "msw";
import { API_BASE_URL } from "@/lib/constants";

const baseUrl = API_BASE_URL;

export const handlers = [
  http.post(`${baseUrl}/auth/login/`, () => {
    return HttpResponse.json({
      access: "mock-access-token",
      refresh: "mock-refresh-token",
      user: {
        id: "user-1",
        email: "doc@test.com",
        first_name: "Jane",
        last_name: "Smith",
        role: "doctor",
        specialty: "Internal Medicine",
        license_number: "",
        practice: "practice-1",
        practice_name: "Test Clinic",
        language_preference: "en",
        created_at: "2026-01-01T00:00:00Z",
      },
    });
  }),

  http.get(`${baseUrl}/auth/user/`, () => {
    return HttpResponse.json({
      id: "user-1",
      email: "doc@test.com",
      first_name: "Jane",
      last_name: "Smith",
      role: "doctor",
      specialty: "Internal Medicine",
      license_number: "",
      practice: "practice-1",
      practice_name: "Test Clinic",
      language_preference: "en",
      created_at: "2026-01-01T00:00:00Z",
    });
  }),

  http.get(`${baseUrl}/encounters/`, () => {
    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: "enc-1",
          doctor: "user-1",
          patient: "patient-1",
          encounter_date: "2026-03-15",
          input_method: "paste",
          status: "ready_for_review",
          consent_recording: false,
          consent_timestamp: null,
          consent_method: "",
          consent_jurisdiction_state: "",
          created_at: "2026-03-15T10:00:00Z",
          updated_at: "2026-03-15T10:00:00Z",
        },
      ],
    });
  }),

  http.get(`${baseUrl}/patients/`, () => {
    return HttpResponse.json({
      count: 1,
      next: null,
      previous: null,
      results: [
        {
          id: "patient-1",
          first_name: "John",
          last_name: "Doe",
          language_preference: "en",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
    });
  }),

  http.get(`${baseUrl}/practice/stats/`, () => {
    return HttpResponse.json({
      total_patients: 10,
      total_encounters: 25,
      encounters_by_status: { approved: 15, delivered: 8, ready_for_review: 2 },
    });
  }),
];
```

File: `web/src/test/mocks/server.ts`
```typescript
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
```

Update `web/src/test/setup.ts`:
```typescript
import "@testing-library/jest-dom/vitest";
import { server } from "./mocks/server";
import { beforeAll, afterEach, afterAll } from "vitest";

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

- [ ] **Step 2 (2 min):** Add MSW dependency and verify.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npm install -D msw
```

Run: `cd web && npm run test:run`
Verify: All tests pass with MSW intercepting requests.

---

## Chunk 15: Final Verification and Cleanup

### Task 15.1: Full build and test suite

- [ ] **Step 1 (2 min):** Run complete test suite.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npm run test:run
```

Verify: All tests pass.

- [ ] **Step 2 (2 min):** Run production build.

```bash
cd /Users/yemalin.godonou/Documents/works/tiko/medicalnote/web
npm run build
```

Verify: Build succeeds without errors.

- [ ] **Step 3 (2 min):** Create `.gitignore` for web directory.

File: `web/.gitignore`
```
node_modules/
.next/
out/
.env.local
.env
*.tsbuildinfo
coverage/
```

- [ ] **Step 4 (1 min):** Verify directory structure matches architecture spec.

```bash
find web/src -type f | head -60
```

Verify: Structure matches `web/src/app/(auth)/`, `web/src/app/(dashboard)/`, `web/src/components/`, `web/src/hooks/`, `web/src/lib/`, `web/src/types/`, `web/src/i18n/`.

---

## Summary of All Files Created

| Category | Files | Count |
|----------|-------|-------|
| **Config** | `vitest.config.ts`, `package.json` scripts, `.env.local.example`, `.gitignore` | 4 |
| **Types** | `types/index.ts` | 1 |
| **Lib** | `constants.ts`, `api-client.ts`, `auth-context.tsx`, `providers.tsx`, `utils.ts` | 5 |
| **Hooks** | `use-job-status.ts`, `use-encounters.ts`, `use-notes.ts`, `use-summaries.ts`, `use-patients.ts`, `use-practice.ts` | 6 |
| **Auth Pages** | `login/page.tsx`, `login/login-form.tsx`, `register/page.tsx`, `register/register-form.tsx`, `(auth)/layout.tsx` | 5 |
| **Dashboard Layout** | `(dashboard)/layout.tsx`, `sidebar.tsx`, `auth-guard.tsx`, `status-badge.tsx` | 4 |
| **Encounter Pages** | `encounters/page.tsx`, `encounters-list.tsx`, `encounters/new/page.tsx`, `new-encounter-form.tsx`, `encounters/[id]/page.tsx`, `encounter-detail.tsx` | 6 |
| **Encounter Components** | `audio-recorder.tsx`, `paste-input.tsx`, `scan-upload.tsx`, `processing-status.tsx`, `summary-preview.tsx` | 5 |
| **Notes Components** | `note-editor.tsx` | 1 |
| **Patient Pages** | `patients/page.tsx`, `patients-list.tsx`, `patients/[id]/page.tsx`, `patient-detail.tsx`, `create-patient-form.tsx` | 5 |
| **Settings** | `settings/page.tsx`, `settings-page.tsx` | 2 |
| **i18n** | `config.ts`, `messages/en.json`, `messages/es.json` | 3 |
| **Tests** | 10 test files + MSW mocks | 12 |
| **Root** | `app/layout.tsx`, `app/page.tsx` | 2 |
| **Total** | | **61** |

### Critical Files for Implementation
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/lib/api-client.ts` - Core typed API client matching all 25+ backend endpoints; every component depends on it
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/types/index.ts` - All TypeScript interfaces mirroring Django models and DRF serializers; used across entire codebase
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/hooks/use-job-status.ts` - WebSocket hook for real-time processing status; critical for the doctor flow UX
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/app/(dashboard)/encounters/[id]/encounter-detail.tsx` - Orchestrates the full review flow: transcript, SOAP note editor, summary preview, and delivery
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/web/src/lib/auth-context.tsx` - JWT token management, auto-refresh, and auth state; gates all protected routes