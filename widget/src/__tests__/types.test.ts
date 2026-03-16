import { describe, it, expect } from "vitest";
import type {
  WidgetEmbedConfig,
  WidgetBrandConfig,
  WidgetSummaryData,
  HostToIframeMessage,
  IframeToHostMessage,
  ThemeVariables,
} from "../types";

describe("types", () => {
  it("WidgetEmbedConfig has required fields", () => {
    const config: WidgetEmbedConfig = {
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    };
    expect(config.widgetKey).toBe("wk_abc123");
    expect(config.theme).toBe("light");
  });

  it("WidgetSummaryData has medical terms array", () => {
    const summary: WidgetSummaryData = {
      id: "uuid-123",
      summary_en: "You visited the doctor.",
      summary_es: "Visitaste al doctor.",
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
    expect(summary.medical_terms_explained).toHaveLength(1);
    expect(summary.medical_terms_explained[0].term).toBe("hypertension");
  });

  it("HostToIframeMessage discriminated union works", () => {
    const msg: HostToIframeMessage = { type: "SET_LANG", lang: "es" };
    expect(msg.type).toBe("SET_LANG");
    if (msg.type === "SET_LANG") {
      expect(msg.lang).toBe("es");
    }
  });

  it("IframeToHostMessage RESIZE includes height", () => {
    const msg: IframeToHostMessage = { type: "RESIZE", height: 500 };
    expect(msg.type).toBe("RESIZE");
    if (msg.type === "RESIZE") {
      expect(msg.height).toBe(500);
    }
  });
});
