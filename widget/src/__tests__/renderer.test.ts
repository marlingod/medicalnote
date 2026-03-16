import { describe, it, expect } from "vitest";
import { renderSummaryHTML, renderLoadingHTML, renderErrorHTML, renderTokenFormHTML } from "../renderer";
import type { WidgetSummaryData, WidgetBrandConfig, ThemeVariables } from "../types";
import { LIGHT_THEME_DEFAULTS } from "../theme";

describe("renderer", () => {
  const mockThemeVars: ThemeVariables = { ...LIGHT_THEME_DEFAULTS };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-123",
    summary_en: "You visited Dr. Smith today. Your blood pressure was normal.",
    summary_es: "Visitaste al Dr. Smith hoy. Su presión arterial fue normal.",
    reading_level: "grade_8",
    medical_terms_explained: [
      { term: "blood pressure", explanation: "the force of blood against artery walls" },
    ],
    disclaimer_text: "This summary is for informational purposes only.",
    encounter_date: "2026-03-15",
    doctor_name: "Dr. Smith",
    delivery_status: "sent",
    viewed_at: null,
    created_at: "2026-03-15T10:00:00Z",
  };

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Test Clinic",
    widget_key: "wk_abc123",
  };

  describe("renderSummaryHTML", () => {
    it("renders summary in English by default", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("You visited Dr. Smith today");
      expect(html).toContain("Dr. Smith");
      expect(html).toContain("2026-03-15");
    });

    it("renders summary in Spanish when lang=es", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "es");
      expect(html).toContain("Visitaste al Dr. Smith hoy");
    });

    it("includes medical term tooltips", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("blood pressure");
      expect(html).toContain("the force of blood against artery walls");
    });

    it("includes disclaimer text", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("informational purposes only");
    });

    it("includes clinic logo when logo_url is set", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain('src="https://cdn.example.com/logo.png"');
    });

    it("includes practice name", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Test Clinic");
    });

    it("includes language toggle buttons", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("English");
      expect(html).toContain("Español");
    });

    it("includes CSP meta tag", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Content-Security-Policy");
      expect(html).toContain("script-src 'self'");
    });

    it("escapes HTML in summary text to prevent XSS", () => {
      const xssSummary: WidgetSummaryData = {
        ...mockSummary,
        summary_en: '<script>alert("xss")</script>',
      };
      const html = renderSummaryHTML(xssSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).not.toContain('<script>alert("xss")</script>');
      expect(html).toContain("&lt;script&gt;");
    });

    it("includes theme CSS variables", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("--mn-brand-color");
      expect(html).toContain("--mn-bg-color");
    });
  });

  describe("renderLoadingHTML", () => {
    it("renders loading state", () => {
      const html = renderLoadingHTML(mockThemeVars, "en");
      expect(html).toContain("Loading");
    });
  });

  describe("renderErrorHTML", () => {
    it("renders error state with message", () => {
      const html = renderErrorHTML("TOKEN_EXPIRED", mockThemeVars, "en");
      expect(html).toContain("expired");
    });

    it("renders generic error for unknown codes", () => {
      const html = renderErrorHTML("UNKNOWN", mockThemeVars, "en");
      expect(html).toContain("Something went wrong");
    });
  });

  describe("renderTokenFormHTML", () => {
    it("renders token input form", () => {
      const html = renderTokenFormHTML(mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Access Code");
      expect(html).toContain("input");
    });
  });
});
