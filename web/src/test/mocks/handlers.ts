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
