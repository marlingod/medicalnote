import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WidgetEmbed } from "../embed";
import type { WidgetEmbedConfig } from "../types";

describe("WidgetEmbed", () => {
  let container: HTMLDivElement;
  const defaultConfig: WidgetEmbedConfig = {
    widgetKey: "wk_abc123",
    theme: "light",
    lang: "en",
    apiBaseUrl: "https://api.medicalnote.app",
    containerId: "medicalnote-widget",
  };

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("creates an iframe inside the container", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();
  });

  it("sets iframe sandbox attributes", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    expect(iframe?.getAttribute("sandbox")).toBe(
      "allow-scripts allow-same-origin"
    );
  });

  it("sets iframe to full width and responsive style", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    expect(iframe?.style.width).toBe("100%");
    expect(iframe?.getAttribute("frameBorder")).toBe("0");
  });

  it("sets iframe title for accessibility", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    expect(iframe?.getAttribute("title")).toBe("MedicalNote Patient Summary");
  });

  it("sets iframe content with srcdoc", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    expect(iframe?.getAttribute("srcdoc")).toBeDefined();
  });

  it("destroy removes the iframe", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    expect(container.querySelector("iframe")).not.toBeNull();
    embed.destroy();
    expect(container.querySelector("iframe")).toBeNull();
  });

  it("does not create duplicate iframes on repeated mount calls", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    embed.mount();
    const iframes = container.querySelectorAll("iframe");
    expect(iframes.length).toBe(1);
  });

  it("throws if container element not found", () => {
    document.body.innerHTML = "";
    const embed = new WidgetEmbed(defaultConfig);
    expect(() => embed.mount()).toThrow("Container element not found");
  });

  it("updateContent changes iframe srcdoc", () => {
    const embed = new WidgetEmbed(defaultConfig);
    embed.mount();
    const iframe = container.querySelector("iframe");
    const initialContent = iframe?.getAttribute("srcdoc");
    embed.updateContent("<html><body>Updated</body></html>");
    const updatedContent = iframe?.getAttribute("srcdoc");
    expect(updatedContent).not.toBe(initialContent);
    expect(updatedContent).toContain("Updated");
  });
});
