import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("Widget Integration", () => {
  let container: HTMLDivElement;
  let scriptTag: HTMLScriptElement;

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Acme Health Clinic",
    widget_key: "wk_integration",
  };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-integration",
    summary_en:
      "You visited Dr. Jones today for a routine checkup. Your vital signs were all within normal range. Your blood pressure was 120/80, which is considered normal.",
    summary_es:
      "Visitaste al Dr. Jones hoy para un chequeo de rutina. Todos sus signos vitales estaban dentro del rango normal. Su presion arterial fue 120/80, lo cual es considerado normal.",
    reading_level: "grade_8",
    medical_terms_explained: [
      {
        term: "blood pressure",
        explanation:
          "the force of blood pushing against the walls of your arteries",
      },
      {
        term: "vital signs",
        explanation:
          "basic body measurements like temperature, heart rate, and blood pressure",
      },
    ],
    disclaimer_text:
      "This summary is for informational purposes only and does not constitute medical advice. Please contact your healthcare provider with any questions.",
    encounter_date: "2026-03-15",
    doctor_name: "Dr. Sarah Jones",
    delivery_status: "sent",
    viewed_at: null,
    created_at: "2026-03-15T14:30:00Z",
  };

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    delete (window as Record<string, unknown>)["MedicalNoteWidget"];
  });

  it("full lifecycle: init -> load config -> show form -> submit token -> show summary -> switch language", async () => {
    // Mock API calls in order: config, summary, mark-read
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSummary),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "viewed" }),
      } as Response);

    // 1. Create controller and init
    const { WidgetController } = await import("../controller");
    const controller = new WidgetController({
      widgetKey: "wk_integration",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();

    // 2. Verify iframe exists
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();

    // 3. Verify token form is shown (since no token in URL)
    let srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Access Code");
    expect(srcdoc).toContain("Acme Health Clinic");

    // 4. Simulate token submission via custom event
    window.dispatchEvent(
      new CustomEvent("medicalnote:token-submit", {
        detail: { token: "signed-token-integration" },
      })
    );

    // Wait for async operations
    await new Promise((resolve) => setTimeout(resolve, 50));

    // 5. Verify summary is displayed
    srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Dr. Sarah Jones");
    expect(srcdoc).toContain("routine checkup");
    expect(srcdoc).toContain("blood pressure");
    expect(srcdoc).toContain("vital signs");
    expect(srcdoc).toContain("informational purposes only");

    // 6. Verify API calls were made
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/widget/config/wk_integration/"),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/widget/summary/signed-token-integration/"),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining(
        "/widget/summary/signed-token-integration/read/"
      ),
      expect.anything()
    );

    // 7. Switch to Spanish
    window.dispatchEvent(
      new CustomEvent("medicalnote:lang-change", {
        detail: { lang: "es" },
      })
    );

    srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Visitaste al Dr. Jones");
    expect(srcdoc).toContain("Su Resumen de Visita");

    // 8. Clean up
    controller.destroy();
    expect(container.querySelector("iframe")).toBeNull();
  });
});
