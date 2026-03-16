import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WidgetApiClient } from "../api";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("WidgetApiClient", () => {
  let client: WidgetApiClient;
  const baseUrl = "https://api.medicalnote.app";

  beforeEach(() => {
    client = new WidgetApiClient(baseUrl);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchWidgetConfig", () => {
    it("fetches config for valid widget key", async () => {
      const mockConfig: WidgetBrandConfig = {
        logo_url: "https://cdn.example.com/logo.png",
        brand_color: "#FF5733",
        custom_domain: "",
        practice_name: "Test Clinic",
        widget_key: "wk_abc123",
      };

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockConfig),
      } as Response);

      const config = await client.fetchWidgetConfig("wk_abc123");
      expect(config).toEqual(mockConfig);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/config/wk_abc123/`,
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            Accept: "application/json",
          }),
        })
      );
    });

    it("throws on invalid widget key (404)", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: "Invalid widget key." }),
      } as Response);

      await expect(client.fetchWidgetConfig("wk_invalid")).rejects.toThrow(
        "Invalid widget key"
      );
    });

    it("throws on network error", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
        new TypeError("Failed to fetch")
      );

      await expect(client.fetchWidgetConfig("wk_abc123")).rejects.toThrow(
        "Network error"
      );
    });
  });

  describe("fetchSummary", () => {
    it("fetches summary for valid token", async () => {
      const mockSummary: WidgetSummaryData = {
        id: "uuid-123",
        summary_en: "You visited Dr. Smith.",
        summary_es: "Visitaste al Dr. Smith.",
        reading_level: "grade_8",
        medical_terms_explained: [
          { term: "hypertension", explanation: "high blood pressure" },
        ],
        disclaimer_text: "For informational purposes only.",
        encounter_date: "2026-03-15",
        doctor_name: "Dr. Smith",
        delivery_status: "sent",
        viewed_at: null,
        created_at: "2026-03-15T10:00:00Z",
      };

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSummary),
      } as Response);

      const summary = await client.fetchSummary("signed-token-xyz");
      expect(summary).toEqual(mockSummary);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/summary/signed-token-xyz/`,
        expect.objectContaining({ method: "GET" })
      );
    });

    it("throws on expired token (403)", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () =>
          Promise.resolve({ error: "Invalid or expired token." }),
      } as Response);

      await expect(client.fetchSummary("expired-token")).rejects.toThrow(
        "expired"
      );
    });
  });

  describe("markSummaryRead", () => {
    it("posts read status", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "viewed" }),
      } as Response);

      await client.markSummaryRead("signed-token-xyz");
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/summary/signed-token-xyz/read/`,
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
