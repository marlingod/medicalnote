import type { WidgetEmbedConfig } from "./types";
/**
 * Parse configuration from script tag data-* attributes.
 * Returns null if the required data-widget-key is missing.
 */
export declare function parseScriptAttributes(scriptElement: HTMLScriptElement): WidgetEmbedConfig | null;
export { WidgetController } from "./controller";
export { WidgetApiClient } from "./api";
export type { WidgetEmbedConfig, WidgetBrandConfig, WidgetSummaryData } from "./types";
