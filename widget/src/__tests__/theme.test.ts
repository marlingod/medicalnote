import { describe, it, expect } from "vitest";
import {
  buildThemeVariables,
  LIGHT_THEME_DEFAULTS,
  DARK_THEME_DEFAULTS,
  generateThemeCSS,
} from "../theme";
import type { WidgetBrandConfig, ThemeVariables } from "../types";

describe("theme", () => {
  const baseBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Test Clinic",
    widget_key: "wk_abc123",
  };

  describe("buildThemeVariables", () => {
    it("returns light theme defaults when theme is light and no brand color", () => {
      const config: WidgetBrandConfig = { ...baseBrandConfig, brand_color: "" };
      const vars = buildThemeVariables(config, "light");
      expect(vars["--mn-bg-color"]).toBe(LIGHT_THEME_DEFAULTS["--mn-bg-color"]);
      expect(vars["--mn-brand-color"]).toBe(
        LIGHT_THEME_DEFAULTS["--mn-brand-color"]
      );
    });

    it("applies brand_color from config", () => {
      const vars = buildThemeVariables(baseBrandConfig, "light");
      expect(vars["--mn-brand-color"]).toBe("#FF5733");
    });

    it("returns dark theme defaults when theme is dark", () => {
      const vars = buildThemeVariables(baseBrandConfig, "dark");
      expect(vars["--mn-bg-color"]).toBe(DARK_THEME_DEFAULTS["--mn-bg-color"]);
      expect(vars["--mn-text-color"]).toBe(
        DARK_THEME_DEFAULTS["--mn-text-color"]
      );
    });

    it("uses brand_color in both light and dark themes", () => {
      const lightVars = buildThemeVariables(baseBrandConfig, "light");
      const darkVars = buildThemeVariables(baseBrandConfig, "dark");
      expect(lightVars["--mn-brand-color"]).toBe("#FF5733");
      expect(darkVars["--mn-brand-color"]).toBe("#FF5733");
    });
  });

  describe("generateThemeCSS", () => {
    it("generates valid CSS custom properties block", () => {
      const vars = buildThemeVariables(baseBrandConfig, "light");
      const css = generateThemeCSS(vars);
      expect(css).toContain(":root");
      expect(css).toContain("--mn-brand-color: #FF5733");
      expect(css).toContain("--mn-bg-color:");
    });
  });
});
