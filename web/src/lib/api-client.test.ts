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
