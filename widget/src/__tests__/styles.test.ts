import { describe, it, expect } from "vitest";
import { WIDGET_STYLES } from "../styles";

describe("styles", () => {
  it("exports a non-empty CSS string", () => {
    expect(WIDGET_STYLES).toBeDefined();
    expect(WIDGET_STYLES.length).toBeGreaterThan(100);
  });

  it("uses CSS custom properties from theme", () => {
    expect(WIDGET_STYLES).toContain("var(--mn-brand-color)");
    expect(WIDGET_STYLES).toContain("var(--mn-bg-color)");
    expect(WIDGET_STYLES).toContain("var(--mn-text-color)");
  });

  it("includes responsive media query", () => {
    expect(WIDGET_STYLES).toContain("@media (max-width: 480px)");
  });

  it("all classes use mn- prefix", () => {
    const classMatches = WIDGET_STYLES.match(/\.[a-z][a-z0-9-]*/g) || [];
    const nonPrefixed = classMatches.filter(
      (cls) => !cls.startsWith(".mn-") && cls !== ".mn"
    );
    expect(nonPrefixed).toEqual([]);
  });
});
