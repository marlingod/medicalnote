import type { WidgetBrandConfig, ThemeVariables } from "./types";
export declare const LIGHT_THEME_DEFAULTS: ThemeVariables;
export declare const DARK_THEME_DEFAULTS: ThemeVariables;
export declare function buildThemeVariables(brandConfig: WidgetBrandConfig, theme: "light" | "dark"): ThemeVariables;
export declare function generateThemeCSS(vars: ThemeVariables): string;
