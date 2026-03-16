import type { WidgetBrandConfig, ThemeVariables } from "./types";

export const LIGHT_THEME_DEFAULTS: ThemeVariables = {
  "--mn-brand-color": "#2563EB",
  "--mn-bg-color": "#FFFFFF",
  "--mn-text-color": "#1F2937",
  "--mn-text-secondary": "#6B7280",
  "--mn-border-color": "#E5E7EB",
  "--mn-surface-color": "#F9FAFB",
  "--mn-tooltip-bg": "#1F2937",
  "--mn-tooltip-text": "#FFFFFF",
  "--mn-font-family":
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};

export const DARK_THEME_DEFAULTS: ThemeVariables = {
  "--mn-brand-color": "#3B82F6",
  "--mn-bg-color": "#111827",
  "--mn-text-color": "#F9FAFB",
  "--mn-text-secondary": "#9CA3AF",
  "--mn-border-color": "#374151",
  "--mn-surface-color": "#1F2937",
  "--mn-tooltip-bg": "#F9FAFB",
  "--mn-tooltip-text": "#1F2937",
  "--mn-font-family":
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
};

export function buildThemeVariables(
  brandConfig: WidgetBrandConfig,
  theme: "light" | "dark"
): ThemeVariables {
  const defaults =
    theme === "dark" ? { ...DARK_THEME_DEFAULTS } : { ...LIGHT_THEME_DEFAULTS };

  if (brandConfig.brand_color) {
    defaults["--mn-brand-color"] = sanitizeColor(brandConfig.brand_color);
  }

  return defaults;
}

export function generateThemeCSS(vars: ThemeVariables): string {
  const properties = Object.entries(vars)
    .map(([key, value]) => `  ${key}: ${value};`)
    .join("\n");

  return `:root {\n${properties}\n}`;
}

/**
 * Validates and sanitizes a CSS color value.
 * Only allows hex colors (#RGB, #RRGGBB, #RRGGBBAA) to prevent CSS injection.
 */
function sanitizeColor(color: string): string {
  const hexPattern = /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$/;
  if (hexPattern.test(color)) {
    return color;
  }
  // Fall back to default brand color if input is invalid
  return LIGHT_THEME_DEFAULTS["--mn-brand-color"];
}
