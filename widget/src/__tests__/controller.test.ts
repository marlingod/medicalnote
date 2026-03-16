import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WidgetController } from "../controller";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("WidgetController", () => {
  let container: HTMLDivElement;

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Test Clinic",
    widget_key: "wk_abc123",
  };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-123",
    summary_en: "You visited Dr. Smith today.",
    summary_es: "Visitaste al Dr. Smith hoy.",
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

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("initializes and fetches widget config", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();
  });

  it("shows token form when no token is provided in URL", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Access Code");
  });

  it("loads summary when token is provided via URL hash", async () => {
    // Simulate token in URL hash
    Object.defineProperty(window, "location", {
      value: { ...window.location, hash: "#token=signed-token-xyz" },
      writable: true,
    });

    vi.spyOn(globalThis, "fetch")
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

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("You visited Dr. Smith today");
  });

  it("shows error when widget config fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: "Invalid widget key." }),
    } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_invalid",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("not found");
  });

  it("destroy cleans up resources", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    expect(container.querySelector("iframe")).not.toBeNull();
    controller.destroy();
    expect(container.querySelector("iframe")).toBeNull();
  });
});
