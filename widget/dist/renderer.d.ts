import type { WidgetSummaryData, WidgetBrandConfig, ThemeVariables } from "./types";
export declare function renderSummaryHTML(summary: WidgetSummaryData, brandConfig: WidgetBrandConfig, themeVars: ThemeVariables, lang: "en" | "es"): string;
export declare function renderLoadingHTML(themeVars: ThemeVariables, lang: "en" | "es"): string;
export declare function renderErrorHTML(errorCode: string, themeVars: ThemeVariables, lang: "en" | "es"): string;
export declare function renderTokenFormHTML(brandConfig: WidgetBrandConfig, themeVars: ThemeVariables, lang: "en" | "es"): string;
