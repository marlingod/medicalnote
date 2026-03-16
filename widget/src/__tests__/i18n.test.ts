import { describe, it, expect } from "vitest";
import { getTranslation, TRANSLATIONS } from "../i18n";

describe("i18n", () => {
  it("returns English translation by default", () => {
    const t = getTranslation("en");
    expect(t.title).toBe("Visit Summary");
    expect(t.disclaimer_label).toBe("Important Notice");
  });

  it("returns Spanish translations", () => {
    const t = getTranslation("es");
    expect(t.title).toBe("Resumen de la Visita");
    expect(t.disclaimer_label).toBe("Aviso Importante");
  });

  it("falls back to English for unknown locale", () => {
    const t = getTranslation("fr" as "en" | "es");
    expect(t.title).toBe("Visit Summary");
  });

  it("has all expected keys for both locales", () => {
    const enKeys = Object.keys(TRANSLATIONS.en);
    const esKeys = Object.keys(TRANSLATIONS.es);
    expect(enKeys).toEqual(esKeys);
  });

  it("includes medical term tooltip labels", () => {
    const t = getTranslation("en");
    expect(t.tooltip_label).toBe("What does this mean?");
  });

  it("includes language toggle labels", () => {
    const t = getTranslation("en");
    expect(t.lang_en).toBe("English");
    expect(t.lang_es).toBe("Español");
  });
});
