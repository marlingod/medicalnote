import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WidgetBrandConfig } from "../types";

describe("index (auto-init)", () => {
  let container: HTMLDivElement;
  let scriptTag: HTMLScriptElement;

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "",
    brand_color: "#2563EB",
    custom_domain: "",
    practice_name: "Test",
    widget_key: "wk_abc123",
  };

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);

    scriptTag = document.createElement("script");
    scriptTag.src = "https://widget.medicalnote.app/v1/widget.js";
    scriptTag.setAttribute("data-widget-key", "wk_abc123");
    scriptTag.setAttribute("data-theme", "light");
    scriptTag.setAttribute("data-lang", "en");
    document.body.appendChild(scriptTag);

    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockBrandConfig),
    } as Response);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    // Clean up any global references
    delete (window as Record<string, unknown>)["MedicalNoteWidget"];
  });

  it("parseScriptAttributes extracts data-* attributes", async () => {
    const { parseScriptAttributes } = await import("../index");
    const config = parseScriptAttributes(scriptTag);
    expect(config).not.toBeNull();
    expect(config?.widgetKey).toBe("wk_abc123");
    expect(config?.theme).toBe("light");
    expect(config?.lang).toBe("en");
  });

  it("parseScriptAttributes returns null for missing widget key", async () => {
    const badScript = document.createElement("script");
    badScript.src = "https://widget.medicalnote.app/v1/widget.js";
    // no data-widget-key
    const { parseScriptAttributes } = await import("../index");
    const config = parseScriptAttributes(badScript);
    expect(config).toBeNull();
  });

  it("parseScriptAttributes defaults theme to light", async () => {
    const minScript = document.createElement("script");
    minScript.src = "https://widget.medicalnote.app/v1/widget.js";
    minScript.setAttribute("data-widget-key", "wk_abc123");
    const { parseScriptAttributes } = await import("../index");
    const config = parseScriptAttributes(minScript);
    expect(config?.theme).toBe("light");
    expect(config?.lang).toBe("en");
  });

  it("parseScriptAttributes validates theme value", async () => {
    scriptTag.setAttribute("data-theme", "invalid");
    const { parseScriptAttributes } = await import("../index");
    const config = parseScriptAttributes(scriptTag);
    expect(config?.theme).toBe("light");
  });

  it("parseScriptAttributes validates lang value", async () => {
    scriptTag.setAttribute("data-lang", "fr");
    const { parseScriptAttributes } = await import("../index");
    const config = parseScriptAttributes(scriptTag);
    expect(config?.lang).toBe("en");
  });
});
