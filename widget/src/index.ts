import type { WidgetEmbedConfig } from "./types";
import { WidgetController } from "./controller";
import {
  DEFAULT_API_BASE_URL,
  DEFAULT_CONTAINER_ID,
  SCRIPT_TAG_SELECTOR,
} from "./constants";

/**
 * Parse configuration from script tag data-* attributes.
 * Returns null if the required data-widget-key is missing.
 */
export function parseScriptAttributes(
  scriptElement: HTMLScriptElement
): WidgetEmbedConfig | null {
  const widgetKey = scriptElement.getAttribute("data-widget-key");
  if (!widgetKey) {
    return null;
  }

  const rawTheme = scriptElement.getAttribute("data-theme") || "light";
  const theme: "light" | "dark" =
    rawTheme === "dark" ? "dark" : "light";

  const rawLang = scriptElement.getAttribute("data-lang") || "en";
  const lang: "en" | "es" =
    rawLang === "es" ? "es" : "en";

  const apiBaseUrl =
    scriptElement.getAttribute("data-api-url") || DEFAULT_API_BASE_URL;

  const containerId =
    scriptElement.getAttribute("data-container") || DEFAULT_CONTAINER_ID;

  return {
    widgetKey,
    theme,
    lang,
    apiBaseUrl,
    containerId,
  };
}

/**
 * Find the widget script tag and auto-initialize.
 * This runs immediately when widget.js is loaded.
 */
function autoInit(): void {
  const scriptTag = document.querySelector(
    SCRIPT_TAG_SELECTOR
  ) as HTMLScriptElement | null;

  if (!scriptTag) {
    console.warn(
      "[MedicalNote Widget] Script tag not found. Ensure the script src contains 'widget.js'."
    );
    return;
  }

  const config = parseScriptAttributes(scriptTag);
  if (!config) {
    console.warn(
      "[MedicalNote Widget] Missing data-widget-key attribute on script tag."
    );
    return;
  }

  const controller = new WidgetController(config);

  // Expose controller for programmatic access
  (window as unknown as Record<string, unknown>)["MedicalNoteWidget"] = {
    controller,
    destroy: () => controller.destroy(),
    version: "1.0.0",
  };

  // Initialize once DOM is ready
  if (
    document.readyState === "complete" ||
    document.readyState === "interactive"
  ) {
    controller.init().catch((err) => {
      console.error("[MedicalNote Widget] Initialization failed:", err);
    });
  } else {
    document.addEventListener("DOMContentLoaded", () => {
      controller.init().catch((err) => {
        console.error("[MedicalNote Widget] Initialization failed:", err);
      });
    });
  }
}

// Auto-initialize
autoInit();

// Named exports for programmatic usage
export { WidgetController } from "./controller";
export { WidgetApiClient } from "./api";
export type { WidgetEmbedConfig, WidgetBrandConfig, WidgetSummaryData } from "./types";
