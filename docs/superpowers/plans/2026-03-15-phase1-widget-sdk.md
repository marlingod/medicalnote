# Phase 1 Widget SDK Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the White-Label Widget SDK -- an embeddable, sandboxed JavaScript widget that clinics add to their website so patients can view visit summaries with clinic branding, medical term tooltips, and EN/ES language toggle.

**Architecture:** A vanilla TypeScript library bundled with Rollup into a single `widget.js` file (<50KB gzipped) hosted on CloudFront CDN. The entry script reads `data-*` attributes, creates a sandboxed iframe, and uses `postMessage` to coordinate between the host page script and the iframe content. The iframe fetches widget config (branding) and summary data from the backend API using a time-limited signed token, then renders the summary with theme engine styling.

**Tech Stack:** TypeScript 5.x, Rollup (bundler), Vitest (testing), jsdom (test DOM), PostCSS (inline CSS), CloudFront CDN (distribution)

---

## Chunk 1: Project Scaffolding and Tooling

### Task 1.1: Initialize the widget package

- [ ] **Step 1 (2 min):** Create the widget directory and initialize `package.json`.

```bash
mkdir -p widget/src widget/src/styles widget/src/__tests__ widget/dist
cd widget
npm init -y
```

Then edit `widget/package.json` to contain:

File: `widget/package.json`
```json
{
  "name": "@medicalnote/widget-sdk",
  "version": "1.0.0",
  "description": "MedicalNote White-Label Patient Summary Widget",
  "main": "dist/widget.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "rollup -c",
    "build:watch": "rollup -c --watch",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "lint": "tsc --noEmit",
    "size": "gzip -c dist/widget.js | wc -c"
  },
  "files": [
    "dist/"
  ],
  "license": "UNLICENSED",
  "private": true,
  "devDependencies": {
    "typescript": "^5.4.0",
    "rollup": "^4.12.0",
    "@rollup/plugin-typescript": "^11.1.0",
    "@rollup/plugin-terser": "^0.4.0",
    "rollup-plugin-postcss": "^4.0.0",
    "tslib": "^2.6.0",
    "vitest": "^1.3.0",
    "jsdom": "^24.0.0",
    "@vitest/coverage-v8": "^1.3.0"
  }
}
```

- [ ] **Step 2 (2 min):** Create TypeScript config.

File: `widget/tsconfig.json`
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "ESNext",
    "moduleResolution": "bundler",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "declaration": true,
    "declarationDir": "dist",
    "outDir": "dist",
    "rootDir": "src",
    "sourceMap": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules", "dist", "src/**/__tests__/**"]
}
```

- [ ] **Step 3 (2 min):** Create Rollup config.

File: `widget/rollup.config.js`
```js
import typescript from "@rollup/plugin-typescript";
import terser from "@rollup/plugin-terser";
import postcss from "rollup-plugin-postcss";

export default {
  input: "src/index.ts",
  output: {
    file: "dist/widget.js",
    format: "iife",
    name: "MedicalNoteWidget",
    sourcemap: true,
  },
  plugins: [
    postcss({
      inject: false,
      extract: false,
      minimize: true,
    }),
    typescript({
      tsconfig: "./tsconfig.json",
      declaration: true,
      declarationDir: "dist",
    }),
    terser({
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
      format: {
        comments: false,
      },
    }),
  ],
};
```

- [ ] **Step 4 (2 min):** Create Vitest config.

File: `widget/vitest.config.ts`
```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/__tests__/**/*.test.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/**/*.ts"],
      exclude: ["src/**/__tests__/**", "src/**/*.d.ts"],
      thresholds: {
        branches: 80,
        functions: 80,
        lines: 80,
        statements: 80,
      },
    },
  },
});
```

- [ ] **Step 5 (2 min):** Install dependencies and verify setup compiles.

```bash
cd widget && npm install
npx tsc --noEmit  # should succeed with no source files yet (only tsconfig)
```

---

## Chunk 2: Type Definitions and Constants

### Task 2.1: Define core types

- [ ] **Step 1 (3 min):** Write failing type compilation test. Create the types file that all modules import.

File: `widget/src/types.ts`
```ts
/** Configuration read from data-* attributes on the script tag */
export interface WidgetEmbedConfig {
  widgetKey: string;
  theme: "light" | "dark";
  lang: "en" | "es";
  apiBaseUrl: string;
  containerId: string;
}

/** Branding config returned from GET /api/v1/widget/config/:widget_key */
export interface WidgetBrandConfig {
  logo_url: string;
  brand_color: string;
  custom_domain: string;
  practice_name: string;
  widget_key: string;
}

/** A single medical term with explanation */
export interface MedicalTermExplained {
  term: string;
  explanation: string;
}

/** Summary data returned from GET /api/v1/widget/summary/:token */
export interface WidgetSummaryData {
  id: string;
  summary_en: string;
  summary_es: string;
  reading_level: "grade_5" | "grade_8" | "grade_12";
  medical_terms_explained: MedicalTermExplained[];
  disclaimer_text: string;
  encounter_date: string;
  doctor_name: string;
  delivery_status: "pending" | "sent" | "viewed" | "failed";
  viewed_at: string | null;
  created_at: string;
}

/** Messages sent from host page script to iframe via postMessage */
export type HostToIframeMessage =
  | { type: "INIT"; config: WidgetEmbedConfig }
  | { type: "SET_TOKEN"; token: string }
  | { type: "SET_LANG"; lang: "en" | "es" };

/** Messages sent from iframe back to host page */
export type IframeToHostMessage =
  | { type: "READY" }
  | { type: "LOADED"; summaryId: string }
  | { type: "ERROR"; code: string; message: string }
  | { type: "RESIZE"; height: number };

/** Theme variables applied to iframe content */
export interface ThemeVariables {
  "--mn-brand-color": string;
  "--mn-bg-color": string;
  "--mn-text-color": string;
  "--mn-text-secondary": string;
  "--mn-border-color": string;
  "--mn-surface-color": string;
  "--mn-tooltip-bg": string;
  "--mn-tooltip-text": string;
  "--mn-font-family": string;
}

/** API error response shape */
export interface ApiError {
  error: string;
}
```

- [ ] **Step 2 (2 min):** Create constants.

File: `widget/src/constants.ts`
```ts
export const WIDGET_VERSION = "v1";
export const DEFAULT_API_BASE_URL = "https://api.medicalnote.app";
export const WIDGET_ORIGIN = "https://widget.medicalnote.app";
export const IFRAME_ID = "medicalnote-widget-iframe";
export const MESSAGE_NAMESPACE = "medicalnote-widget";
export const TOKEN_MAX_AGE_MS = 24 * 60 * 60 * 1000; // 24 hours
export const DEFAULT_CONTAINER_ID = "medicalnote-widget";
export const SCRIPT_TAG_SELECTOR = 'script[src*="widget.js"]';
export const MAX_IFRAME_HEIGHT = 2000;
export const MIN_IFRAME_HEIGHT = 200;
```

- [ ] **Step 3 (2 min):** Write a type-check test that verifies the types compile correctly.

File: `widget/src/__tests__/types.test.ts`
```ts
import { describe, it, expect } from "vitest";
import type {
  WidgetEmbedConfig,
  WidgetBrandConfig,
  WidgetSummaryData,
  HostToIframeMessage,
  IframeToHostMessage,
  ThemeVariables,
} from "../types";

describe("types", () => {
  it("WidgetEmbedConfig has required fields", () => {
    const config: WidgetEmbedConfig = {
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    };
    expect(config.widgetKey).toBe("wk_abc123");
    expect(config.theme).toBe("light");
  });

  it("WidgetSummaryData has medical terms array", () => {
    const summary: WidgetSummaryData = {
      id: "uuid-123",
      summary_en: "You visited the doctor.",
      summary_es: "Visitaste al doctor.",
      reading_level: "grade_8",
      medical_terms_explained: [
        { term: "hypertension", explanation: "high blood pressure" },
      ],
      disclaimer_text: "For informational purposes only.",
      encounter_date: "2026-03-15",
      doctor_name: "Dr. Smith",
      delivery_status: "sent",
      viewed_at: null,
      created_at: "2026-03-15T10:00:00Z",
    };
    expect(summary.medical_terms_explained).toHaveLength(1);
    expect(summary.medical_terms_explained[0].term).toBe("hypertension");
  });

  it("HostToIframeMessage discriminated union works", () => {
    const msg: HostToIframeMessage = { type: "SET_LANG", lang: "es" };
    expect(msg.type).toBe("SET_LANG");
    if (msg.type === "SET_LANG") {
      expect(msg.lang).toBe("es");
    }
  });

  it("IframeToHostMessage RESIZE includes height", () => {
    const msg: IframeToHostMessage = { type: "RESIZE", height: 500 };
    expect(msg.type).toBe("RESIZE");
    if (msg.type === "RESIZE") {
      expect(msg.height).toBe(500);
    }
  });
});
```

Run: `cd widget && npx vitest run src/__tests__/types.test.ts`
Verify: All 4 tests pass.

---

## Chunk 3: API Client

### Task 3.1: Build the API client with zero dependencies

- [ ] **Step 1 (3 min):** Write failing tests for the API client.

File: `widget/src/__tests__/api.test.ts`
```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WidgetApiClient } from "../api";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("WidgetApiClient", () => {
  let client: WidgetApiClient;
  const baseUrl = "https://api.medicalnote.app";

  beforeEach(() => {
    client = new WidgetApiClient(baseUrl);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("fetchWidgetConfig", () => {
    it("fetches config for valid widget key", async () => {
      const mockConfig: WidgetBrandConfig = {
        logo_url: "https://cdn.example.com/logo.png",
        brand_color: "#FF5733",
        custom_domain: "",
        practice_name: "Test Clinic",
        widget_key: "wk_abc123",
      };

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockConfig),
      } as Response);

      const config = await client.fetchWidgetConfig("wk_abc123");
      expect(config).toEqual(mockConfig);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/config/wk_abc123/`,
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            Accept: "application/json",
          }),
        })
      );
    });

    it("throws on invalid widget key (404)", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 404,
        json: () => Promise.resolve({ error: "Invalid widget key." }),
      } as Response);

      await expect(client.fetchWidgetConfig("wk_invalid")).rejects.toThrow(
        "Invalid widget key"
      );
    });

    it("throws on network error", async () => {
      vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(
        new TypeError("Failed to fetch")
      );

      await expect(client.fetchWidgetConfig("wk_abc123")).rejects.toThrow(
        "Network error"
      );
    });
  });

  describe("fetchSummary", () => {
    it("fetches summary for valid token", async () => {
      const mockSummary: WidgetSummaryData = {
        id: "uuid-123",
        summary_en: "You visited Dr. Smith.",
        summary_es: "Visitaste al Dr. Smith.",
        reading_level: "grade_8",
        medical_terms_explained: [
          { term: "hypertension", explanation: "high blood pressure" },
        ],
        disclaimer_text: "For informational purposes only.",
        encounter_date: "2026-03-15",
        doctor_name: "Dr. Smith",
        delivery_status: "sent",
        viewed_at: null,
        created_at: "2026-03-15T10:00:00Z",
      };

      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSummary),
      } as Response);

      const summary = await client.fetchSummary("signed-token-xyz");
      expect(summary).toEqual(mockSummary);
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/summary/signed-token-xyz/`,
        expect.objectContaining({ method: "GET" })
      );
    });

    it("throws on expired token (403)", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: () =>
          Promise.resolve({ error: "Invalid or expired token." }),
      } as Response);

      await expect(client.fetchSummary("expired-token")).rejects.toThrow(
        "expired"
      );
    });
  });

  describe("markSummaryRead", () => {
    it("posts read status", async () => {
      vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "viewed" }),
      } as Response);

      await client.markSummaryRead("signed-token-xyz");
      expect(globalThis.fetch).toHaveBeenCalledWith(
        `${baseUrl}/api/v1/widget/summary/signed-token-xyz/read/`,
        expect.objectContaining({ method: "POST" })
      );
    });
  });
});
```

Run: `cd widget && npx vitest run src/__tests__/api.test.ts`
Verify: Tests fail (module not found).

- [ ] **Step 2 (4 min):** Implement the API client.

File: `widget/src/api.ts`
```ts
import type { WidgetBrandConfig, WidgetSummaryData } from "./types";

export class WidgetApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code: string
  ) {
    super(message);
    this.name = "WidgetApiError";
  }
}

export class WidgetApiClient {
  private readonly baseUrl: string;

  constructor(baseUrl: string) {
    // Remove trailing slash if present
    this.baseUrl = baseUrl.replace(/\/+$/, "");
  }

  async fetchWidgetConfig(widgetKey: string): Promise<WidgetBrandConfig> {
    const url = `${this.baseUrl}/api/v1/widget/config/${encodeURIComponent(widgetKey)}/`;
    const response = await this.request(url, "GET");
    return response as WidgetBrandConfig;
  }

  async fetchSummary(token: string): Promise<WidgetSummaryData> {
    const url = `${this.baseUrl}/api/v1/widget/summary/${encodeURIComponent(token)}/`;
    const response = await this.request(url, "GET");
    return response as WidgetSummaryData;
  }

  async markSummaryRead(token: string): Promise<void> {
    const url = `${this.baseUrl}/api/v1/widget/summary/${encodeURIComponent(token)}/read/`;
    await this.request(url, "POST");
  }

  private async request(
    url: string,
    method: "GET" | "POST"
  ): Promise<unknown> {
    let response: Response;

    try {
      response = await fetch(url, {
        method,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        credentials: "omit",
      });
    } catch {
      throw new WidgetApiError(
        "Network error: unable to reach MedicalNote servers.",
        0,
        "NETWORK_ERROR"
      );
    }

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      let errorCode = "UNKNOWN_ERROR";

      try {
        const errorBody = await response.json();
        if (errorBody.error) {
          errorMessage = errorBody.error;
        }
      } catch {
        // Response body is not JSON, use default message
      }

      if (response.status === 404) {
        errorCode = "NOT_FOUND";
        errorMessage = errorMessage || "Invalid widget key";
      } else if (response.status === 403) {
        errorCode = "TOKEN_EXPIRED";
        errorMessage = errorMessage || "Token expired or invalid";
      } else if (response.status === 429) {
        errorCode = "RATE_LIMITED";
        errorMessage = "Too many requests. Please try again later.";
      }

      throw new WidgetApiError(errorMessage, response.status, errorCode);
    }

    return response.json();
  }
}
```

Run: `cd widget && npx vitest run src/__tests__/api.test.ts`
Verify: All 6 tests pass.

---

## Chunk 4: Theme Engine

### Task 4.1: Build the theme engine that applies clinic branding

- [ ] **Step 1 (3 min):** Write failing tests.

File: `widget/src/__tests__/theme.test.ts`
```ts
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
```

Run: `cd widget && npx vitest run src/__tests__/theme.test.ts`
Verify: Tests fail (module not found).

- [ ] **Step 2 (4 min):** Implement the theme engine.

File: `widget/src/theme.ts`
```ts
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
```

Run: `cd widget && npx vitest run src/__tests__/theme.test.ts`
Verify: All 5 tests pass.

---

## Chunk 5: Internationalization (i18n)

### Task 5.1: Build the i18n module for EN/ES toggle

- [ ] **Step 1 (3 min):** Write failing tests.

File: `widget/src/__tests__/i18n.test.ts`
```ts
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
```

Run: `cd widget && npx vitest run src/__tests__/i18n.test.ts`
Verify: Tests fail.

- [ ] **Step 2 (3 min):** Implement i18n module.

File: `widget/src/i18n.ts`
```ts
export interface TranslationStrings {
  title: string;
  subtitle_date: string;
  subtitle_doctor: string;
  summary_heading: string;
  disclaimer_label: string;
  tooltip_label: string;
  lang_en: string;
  lang_es: string;
  loading: string;
  error_expired: string;
  error_not_found: string;
  error_network: string;
  error_generic: string;
  powered_by: string;
  enter_token_label: string;
  enter_token_placeholder: string;
  submit_button: string;
  medical_terms_heading: string;
}

export const TRANSLATIONS: Record<"en" | "es", TranslationStrings> = {
  en: {
    title: "Visit Summary",
    subtitle_date: "Date",
    subtitle_doctor: "Provider",
    summary_heading: "Your Visit Summary",
    disclaimer_label: "Important Notice",
    tooltip_label: "What does this mean?",
    lang_en: "English",
    lang_es: "Español",
    loading: "Loading your visit summary...",
    error_expired:
      "This link has expired. Please request a new summary link from your clinic.",
    error_not_found: "Summary not found. Please check your link and try again.",
    error_network:
      "Unable to connect. Please check your internet connection and try again.",
    error_generic: "Something went wrong. Please try again later.",
    powered_by: "Powered by MedicalNote",
    enter_token_label: "Access Code",
    enter_token_placeholder: "Enter your access code",
    submit_button: "View Summary",
    medical_terms_heading: "Medical Terms Explained",
  },
  es: {
    title: "Resumen de la Visita",
    subtitle_date: "Fecha",
    subtitle_doctor: "Proveedor",
    summary_heading: "Su Resumen de Visita",
    disclaimer_label: "Aviso Importante",
    tooltip_label: "¿Qué significa esto?",
    lang_en: "English",
    lang_es: "Español",
    loading: "Cargando su resumen de visita...",
    error_expired:
      "Este enlace ha expirado. Solicite un nuevo enlace de resumen a su clínica.",
    error_not_found:
      "Resumen no encontrado. Verifique su enlace e intente de nuevo.",
    error_network:
      "No se puede conectar. Verifique su conexión a internet e intente de nuevo.",
    error_generic: "Algo salió mal. Intente de nuevo más tarde.",
    powered_by: "Desarrollado por MedicalNote",
    enter_token_label: "Código de Acceso",
    enter_token_placeholder: "Ingrese su código de acceso",
    submit_button: "Ver Resumen",
    medical_terms_heading: "Términos Médicos Explicados",
  },
};

export function getTranslation(lang: "en" | "es"): TranslationStrings {
  return TRANSLATIONS[lang] ?? TRANSLATIONS.en;
}
```

Run: `cd widget && npx vitest run src/__tests__/i18n.test.ts`
Verify: All 6 tests pass.

---

## Chunk 6: iframe Content Renderer

### Task 6.1: Build the HTML renderer that generates iframe content

- [ ] **Step 1 (4 min):** Write failing tests for the renderer.

File: `widget/src/__tests__/renderer.test.ts`
```ts
import { describe, it, expect } from "vitest";
import { renderSummaryHTML, renderLoadingHTML, renderErrorHTML, renderTokenFormHTML } from "../renderer";
import type { WidgetSummaryData, WidgetBrandConfig, ThemeVariables } from "../types";
import { LIGHT_THEME_DEFAULTS } from "../theme";

describe("renderer", () => {
  const mockThemeVars: ThemeVariables = { ...LIGHT_THEME_DEFAULTS };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-123",
    summary_en: "You visited Dr. Smith today. Your blood pressure was normal.",
    summary_es: "Visitaste al Dr. Smith hoy. Su presión arterial fue normal.",
    reading_level: "grade_8",
    medical_terms_explained: [
      { term: "blood pressure", explanation: "the force of blood against artery walls" },
    ],
    disclaimer_text: "This summary is for informational purposes only.",
    encounter_date: "2026-03-15",
    doctor_name: "Dr. Smith",
    delivery_status: "sent",
    viewed_at: null,
    created_at: "2026-03-15T10:00:00Z",
  };

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Test Clinic",
    widget_key: "wk_abc123",
  };

  describe("renderSummaryHTML", () => {
    it("renders summary in English by default", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("You visited Dr. Smith today");
      expect(html).toContain("Dr. Smith");
      expect(html).toContain("2026-03-15");
    });

    it("renders summary in Spanish when lang=es", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "es");
      expect(html).toContain("Visitaste al Dr. Smith hoy");
    });

    it("includes medical term tooltips", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("blood pressure");
      expect(html).toContain("the force of blood against artery walls");
    });

    it("includes disclaimer text", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("informational purposes only");
    });

    it("includes clinic logo when logo_url is set", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain('src="https://cdn.example.com/logo.png"');
    });

    it("includes practice name", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Test Clinic");
    });

    it("includes language toggle buttons", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("English");
      expect(html).toContain("Español");
    });

    it("includes CSP meta tag", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Content-Security-Policy");
      expect(html).toContain("script-src 'self'");
    });

    it("escapes HTML in summary text to prevent XSS", () => {
      const xssSummary: WidgetSummaryData = {
        ...mockSummary,
        summary_en: '<script>alert("xss")</script>',
      };
      const html = renderSummaryHTML(xssSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).not.toContain('<script>alert("xss")</script>');
      expect(html).toContain("&lt;script&gt;");
    });

    it("includes theme CSS variables", () => {
      const html = renderSummaryHTML(mockSummary, mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("--mn-brand-color");
      expect(html).toContain("--mn-bg-color");
    });
  });

  describe("renderLoadingHTML", () => {
    it("renders loading state", () => {
      const html = renderLoadingHTML(mockThemeVars, "en");
      expect(html).toContain("Loading");
    });
  });

  describe("renderErrorHTML", () => {
    it("renders error state with message", () => {
      const html = renderErrorHTML("TOKEN_EXPIRED", mockThemeVars, "en");
      expect(html).toContain("expired");
    });

    it("renders generic error for unknown codes", () => {
      const html = renderErrorHTML("UNKNOWN", mockThemeVars, "en");
      expect(html).toContain("Something went wrong");
    });
  });

  describe("renderTokenFormHTML", () => {
    it("renders token input form", () => {
      const html = renderTokenFormHTML(mockBrandConfig, mockThemeVars, "en");
      expect(html).toContain("Access Code");
      expect(html).toContain("input");
    });
  });
});
```

Run: `cd widget && npx vitest run src/__tests__/renderer.test.ts`
Verify: Tests fail.

- [ ] **Step 2 (5 min):** Implement the renderer.

File: `widget/src/renderer.ts`
```ts
import type {
  WidgetSummaryData,
  WidgetBrandConfig,
  ThemeVariables,
} from "./types";
import { getTranslation } from "./i18n";
import { generateThemeCSS } from "./theme";
import { WIDGET_STYLES } from "./styles";

/** Escape HTML to prevent XSS */
function escapeHTML(str: string): string {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

/** Shared CSP meta tag for all iframe pages */
function cspMetaTag(): string {
  return `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; script-src 'self'; connect-src 'none'; font-src 'none'; frame-src 'none';">`;
}

/** Shared <head> block */
function headBlock(themeVars: ThemeVariables, lang: "en" | "es"): string {
  return `<!DOCTYPE html>
<html lang="${lang}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  ${cspMetaTag()}
  <style>${generateThemeCSS(themeVars)}\n${WIDGET_STYLES}</style>
</head>`;
}

export function renderSummaryHTML(
  summary: WidgetSummaryData,
  brandConfig: WidgetBrandConfig,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  const summaryText =
    lang === "es" && summary.summary_es
      ? summary.summary_es
      : summary.summary_en;

  const logoHTML = brandConfig.logo_url
    ? `<img class="mn-logo" src="${escapeHTML(brandConfig.logo_url)}" alt="${escapeHTML(brandConfig.practice_name)} logo" />`
    : "";

  const termsHTML =
    summary.medical_terms_explained.length > 0
      ? `<div class="mn-terms">
          <h3 class="mn-terms-heading">${escapeHTML(t.medical_terms_heading)}</h3>
          <dl class="mn-terms-list">
            ${summary.medical_terms_explained
              .map(
                (term) =>
                  `<dt class="mn-term">${escapeHTML(term.term)}</dt>
                   <dd class="mn-term-explanation">${escapeHTML(term.explanation)}</dd>`
              )
              .join("")}
          </dl>
        </div>`
      : "";

  const langToggleHTML = `<div class="mn-lang-toggle">
    <button class="mn-lang-btn ${lang === "en" ? "mn-lang-active" : ""}" data-lang="en">${t.lang_en}</button>
    <button class="mn-lang-btn ${lang === "es" ? "mn-lang-active" : ""}" data-lang="es">${t.lang_es}</button>
  </div>`;

  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container">
    <header class="mn-header">
      ${logoHTML}
      <h1 class="mn-practice-name">${escapeHTML(brandConfig.practice_name)}</h1>
      ${langToggleHTML}
    </header>

    <div class="mn-meta">
      <span class="mn-meta-item"><strong>${escapeHTML(t.subtitle_date)}:</strong> ${escapeHTML(summary.encounter_date)}</span>
      <span class="mn-meta-item"><strong>${escapeHTML(t.subtitle_doctor)}:</strong> ${escapeHTML(summary.doctor_name)}</span>
    </div>

    <main class="mn-summary">
      <h2 class="mn-summary-heading">${escapeHTML(t.summary_heading)}</h2>
      <div class="mn-summary-text">${escapeHTML(summaryText)}</div>
    </main>

    ${termsHTML}

    <div class="mn-disclaimer">
      <strong>${escapeHTML(t.disclaimer_label)}:</strong>
      ${escapeHTML(summary.disclaimer_text)}
    </div>

    <footer class="mn-footer">
      <span class="mn-powered-by">${escapeHTML(t.powered_by)}</span>
    </footer>
  </div>

  <script>
    document.querySelectorAll('.mn-lang-btn').forEach(function(btn) {
      btn.addEventListener('click', function() {
        var lang = btn.getAttribute('data-lang');
        window.parent.postMessage({ ns: 'medicalnote-widget', type: 'SET_LANG', lang: lang }, '*');
      });
    });

    // Notify parent of content height for auto-resize
    var height = document.querySelector('.mn-container').scrollHeight;
    window.parent.postMessage({ ns: 'medicalnote-widget', type: 'RESIZE', height: height }, '*');
  </script>
</body>
</html>`;
}

export function renderLoadingHTML(
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-loading">
    <div class="mn-spinner"></div>
    <p class="mn-loading-text">${escapeHTML(t.loading)}</p>
  </div>
</body>
</html>`;
}

export function renderErrorHTML(
  errorCode: string,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  let message: string;
  switch (errorCode) {
    case "TOKEN_EXPIRED":
      message = t.error_expired;
      break;
    case "NOT_FOUND":
      message = t.error_not_found;
      break;
    case "NETWORK_ERROR":
      message = t.error_network;
      break;
    default:
      message = t.error_generic;
      break;
  }
  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-error">
    <div class="mn-error-icon">&#9888;</div>
    <p class="mn-error-text">${escapeHTML(message)}</p>
  </div>
</body>
</html>`;
}

export function renderTokenFormHTML(
  brandConfig: WidgetBrandConfig,
  themeVars: ThemeVariables,
  lang: "en" | "es"
): string {
  const t = getTranslation(lang);
  const logoHTML = brandConfig.logo_url
    ? `<img class="mn-logo" src="${escapeHTML(brandConfig.logo_url)}" alt="${escapeHTML(brandConfig.practice_name)} logo" />`
    : "";

  return `${headBlock(themeVars, lang)}
<body class="mn-body">
  <div class="mn-container mn-token-form">
    <header class="mn-header">
      ${logoHTML}
      <h1 class="mn-practice-name">${escapeHTML(brandConfig.practice_name)}</h1>
    </header>
    <form class="mn-form" id="mn-token-form">
      <label class="mn-label" for="mn-token-input">${escapeHTML(t.enter_token_label)}</label>
      <input class="mn-input" id="mn-token-input" type="text" placeholder="${escapeHTML(t.enter_token_placeholder)}" autocomplete="off" required />
      <button class="mn-submit-btn" type="submit">${escapeHTML(t.submit_button)}</button>
    </form>
    <footer class="mn-footer">
      <span class="mn-powered-by">${escapeHTML(t.powered_by)}</span>
    </footer>
  </div>

  <script>
    document.getElementById('mn-token-form').addEventListener('submit', function(e) {
      e.preventDefault();
      var token = document.getElementById('mn-token-input').value.trim();
      if (token) {
        window.parent.postMessage({ ns: 'medicalnote-widget', type: 'SET_TOKEN', token: token }, '*');
      }
    });
  </script>
</body>
</html>`;
}
```

Run: `cd widget && npx vitest run src/__tests__/renderer.test.ts`
Verify: All tests pass.

---

## Chunk 7: Widget Styles (Inline CSS)

### Task 7.1: Create the widget CSS styles

- [ ] **Step 1 (4 min):** Create the styles module that will be inlined into the iframe.

File: `widget/src/styles.ts`
```ts
/**
 * All widget CSS, inlined into the iframe <style> tag.
 * Uses CSS custom properties defined by the theme engine.
 * All classes prefixed with mn- to avoid collisions.
 */
export const WIDGET_STYLES = `
/* Reset */
*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

.mn-body {
  font-family: var(--mn-font-family);
  background-color: var(--mn-bg-color);
  color: var(--mn-text-color);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.mn-container {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 20px;
}

/* Header */
.mn-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--mn-border-color);
}

.mn-logo {
  height: 40px;
  width: auto;
  max-width: 120px;
  object-fit: contain;
}

.mn-practice-name {
  font-size: 18px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
}

/* Language toggle */
.mn-lang-toggle {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.mn-lang-btn {
  background: transparent;
  border: 1px solid var(--mn-border-color);
  border-radius: 4px;
  padding: 4px 10px;
  font-size: 13px;
  cursor: pointer;
  color: var(--mn-text-secondary);
  transition: all 0.15s ease;
}

.mn-lang-btn:hover {
  border-color: var(--mn-brand-color);
  color: var(--mn-brand-color);
}

.mn-lang-active {
  background-color: var(--mn-brand-color);
  border-color: var(--mn-brand-color);
  color: #FFFFFF;
}

.mn-lang-active:hover {
  color: #FFFFFF;
}

/* Meta info (date, doctor) */
.mn-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
  font-size: 14px;
  color: var(--mn-text-secondary);
}

.mn-meta-item strong {
  color: var(--mn-text-color);
}

/* Summary */
.mn-summary {
  margin-bottom: 24px;
}

.mn-summary-heading {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--mn-brand-color);
}

.mn-summary-text {
  font-size: 15px;
  line-height: 1.7;
  white-space: pre-wrap;
}

/* Medical terms */
.mn-terms {
  background-color: var(--mn-surface-color);
  border: 1px solid var(--mn-border-color);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.mn-terms-heading {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--mn-brand-color);
}

.mn-terms-list {
  display: grid;
  gap: 8px;
}

.mn-term {
  font-weight: 600;
  font-size: 14px;
  color: var(--mn-text-color);
}

.mn-term-explanation {
  font-size: 13px;
  color: var(--mn-text-secondary);
  margin-left: 0;
  margin-bottom: 8px;
  padding-left: 12px;
  border-left: 2px solid var(--mn-brand-color);
}

/* Disclaimer */
.mn-disclaimer {
  background-color: var(--mn-surface-color);
  border: 1px solid var(--mn-border-color);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--mn-text-secondary);
  margin-bottom: 20px;
}

.mn-disclaimer strong {
  color: var(--mn-text-color);
}

/* Footer */
.mn-footer {
  text-align: center;
  padding-top: 16px;
  border-top: 1px solid var(--mn-border-color);
}

.mn-powered-by {
  font-size: 12px;
  color: var(--mn-text-secondary);
}

/* Loading state */
.mn-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 16px;
}

.mn-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--mn-border-color);
  border-top-color: var(--mn-brand-color);
  border-radius: 50%;
  animation: mn-spin 0.8s linear infinite;
}

@keyframes mn-spin {
  to { transform: rotate(360deg); }
}

.mn-loading-text {
  font-size: 14px;
  color: var(--mn-text-secondary);
}

/* Error state */
.mn-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  gap: 12px;
  text-align: center;
}

.mn-error-icon {
  font-size: 36px;
  color: var(--mn-text-secondary);
}

.mn-error-text {
  font-size: 14px;
  color: var(--mn-text-secondary);
  max-width: 400px;
}

/* Token form */
.mn-token-form .mn-form {
  max-width: 360px;
  margin: 24px auto;
}

.mn-label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.mn-input {
  display: block;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--mn-border-color);
  border-radius: 6px;
  font-size: 15px;
  background-color: var(--mn-bg-color);
  color: var(--mn-text-color);
  margin-bottom: 12px;
  outline: none;
  transition: border-color 0.15s ease;
}

.mn-input:focus {
  border-color: var(--mn-brand-color);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--mn-brand-color) 20%, transparent);
}

.mn-submit-btn {
  display: block;
  width: 100%;
  padding: 10px 16px;
  background-color: var(--mn-brand-color);
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s ease;
}

.mn-submit-btn:hover {
  opacity: 0.9;
}

/* Responsive */
@media (max-width: 480px) {
  .mn-container {
    padding: 16px 12px;
  }

  .mn-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .mn-lang-toggle {
    margin-left: 0;
  }

  .mn-meta {
    flex-direction: column;
    gap: 4px;
  }
}
`;
```

- [ ] **Step 2 (2 min):** Write a simple test for styles.

File: `widget/src/__tests__/styles.test.ts`
```ts
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
```

Run: `cd widget && npx vitest run src/__tests__/styles.test.ts`
Verify: All 4 tests pass.

---

## Chunk 8: Embed Module (iframe creation + postMessage)

### Task 8.1: Build the embed module that creates and manages the iframe

- [ ] **Step 1 (4 min):** Write failing tests.

File: `widget/src/__tests__/embed.test.ts`
```ts
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
    expect(iframe?.style.border).toBe("none");
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
```

Run: `cd widget && npx vitest run src/__tests__/embed.test.ts`
Verify: Tests fail.

- [ ] **Step 2 (5 min):** Implement the embed module.

File: `widget/src/embed.ts`
```ts
import type { WidgetEmbedConfig } from "./types";
import { IFRAME_ID, MAX_IFRAME_HEIGHT, MIN_IFRAME_HEIGHT, MESSAGE_NAMESPACE } from "./constants";
import { renderLoadingHTML } from "./renderer";
import { buildThemeVariables } from "./theme";
import { LIGHT_THEME_DEFAULTS } from "./theme";

export class WidgetEmbed {
  private readonly config: WidgetEmbedConfig;
  private iframe: HTMLIFrameElement | null = null;
  private messageHandler: ((event: MessageEvent) => void) | null = null;

  constructor(config: WidgetEmbedConfig) {
    this.config = config;
  }

  mount(): void {
    const container = document.getElementById(this.config.containerId);
    if (!container) {
      throw new Error(
        `Container element not found: #${this.config.containerId}`
      );
    }

    // Prevent duplicate iframes
    if (this.iframe && container.contains(this.iframe)) {
      return;
    }

    this.iframe = document.createElement("iframe");
    this.iframe.id = IFRAME_ID;
    this.iframe.title = "MedicalNote Patient Summary";
    this.iframe.setAttribute("sandbox", "allow-scripts allow-same-origin");
    this.iframe.style.width = "100%";
    this.iframe.style.border = "none";
    this.iframe.style.overflow = "hidden";
    this.iframe.style.minHeight = `${MIN_IFRAME_HEIGHT}px`;
    this.iframe.style.maxHeight = `${MAX_IFRAME_HEIGHT}px`;
    this.iframe.setAttribute("loading", "lazy");
    this.iframe.setAttribute("importance", "high");

    // Set initial loading content
    const themeVars = buildThemeVariables(
      {
        logo_url: "",
        brand_color: "",
        custom_domain: "",
        practice_name: "",
        widget_key: this.config.widgetKey,
      },
      this.config.theme
    );
    const loadingHTML = renderLoadingHTML(themeVars, this.config.lang);
    this.iframe.setAttribute("srcdoc", loadingHTML);

    container.appendChild(this.iframe);

    this.setupMessageListener();
  }

  updateContent(html: string): void {
    if (this.iframe) {
      this.iframe.setAttribute("srcdoc", html);
    }
  }

  setHeight(height: number): void {
    if (this.iframe) {
      const clampedHeight = Math.min(
        Math.max(height, MIN_IFRAME_HEIGHT),
        MAX_IFRAME_HEIGHT
      );
      this.iframe.style.height = `${clampedHeight}px`;
    }
  }

  destroy(): void {
    if (this.messageHandler) {
      window.removeEventListener("message", this.messageHandler);
      this.messageHandler = null;
    }
    if (this.iframe) {
      this.iframe.remove();
      this.iframe = null;
    }
  }

  private setupMessageListener(): void {
    this.messageHandler = (event: MessageEvent) => {
      const data = event.data;
      if (!data || data.ns !== MESSAGE_NAMESPACE) {
        return;
      }

      switch (data.type) {
        case "RESIZE":
          if (typeof data.height === "number") {
            this.setHeight(data.height);
          }
          break;
        case "SET_LANG":
          if (data.lang === "en" || data.lang === "es") {
            // Dispatch custom event so the widget controller can handle lang change
            const langEvent = new CustomEvent("medicalnote:lang-change", {
              detail: { lang: data.lang },
            });
            window.dispatchEvent(langEvent);
          }
          break;
        case "SET_TOKEN":
          if (typeof data.token === "string" && data.token.length > 0) {
            const tokenEvent = new CustomEvent("medicalnote:token-submit", {
              detail: { token: data.token },
            });
            window.dispatchEvent(tokenEvent);
          }
          break;
      }
    };

    window.addEventListener("message", this.messageHandler);
  }
}
```

Run: `cd widget && npx vitest run src/__tests__/embed.test.ts`
Verify: All 9 tests pass.

---

## Chunk 9: Widget Controller (Main Entry Point)

### Task 9.1: Build the widget controller that orchestrates all modules

- [ ] **Step 1 (4 min):** Write failing tests.

File: `widget/src/__tests__/controller.test.ts`
```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WidgetController } from "../controller";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("WidgetController", () => {
  let container: HTMLDivElement;

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Test Clinic",
    widget_key: "wk_abc123",
  };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-123",
    summary_en: "You visited Dr. Smith today.",
    summary_es: "Visitaste al Dr. Smith hoy.",
    reading_level: "grade_8",
    medical_terms_explained: [
      { term: "hypertension", explanation: "high blood pressure" },
    ],
    disclaimer_text: "For informational purposes only.",
    encounter_date: "2026-03-15",
    doctor_name: "Dr. Smith",
    delivery_status: "sent",
    viewed_at: null,
    created_at: "2026-03-15T10:00:00Z",
  };

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
  });

  it("initializes and fetches widget config", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();
  });

  it("shows token form when no token is provided in URL", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Access Code");
  });

  it("loads summary when token is provided via URL hash", async () => {
    // Simulate token in URL hash
    Object.defineProperty(window, "location", {
      value: { ...window.location, hash: "#token=signed-token-xyz" },
      writable: true,
    });

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSummary),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "viewed" }),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("You visited Dr. Smith today");
  });

  it("shows error when widget config fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ error: "Invalid widget key." }),
    } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_invalid",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    const iframe = container.querySelector("iframe");
    const srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Something went wrong");
  });

  it("destroy cleans up resources", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response);

    const controller = new WidgetController({
      widgetKey: "wk_abc123",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();
    expect(container.querySelector("iframe")).not.toBeNull();
    controller.destroy();
    expect(container.querySelector("iframe")).toBeNull();
  });
});
```

Run: `cd widget && npx vitest run src/__tests__/controller.test.ts`
Verify: Tests fail.

- [ ] **Step 2 (5 min):** Implement the widget controller.

File: `widget/src/controller.ts`
```ts
import type {
  WidgetEmbedConfig,
  WidgetBrandConfig,
  WidgetSummaryData,
} from "./types";
import { WidgetApiClient, WidgetApiError } from "./api";
import { WidgetEmbed } from "./embed";
import { buildThemeVariables } from "./theme";
import {
  renderSummaryHTML,
  renderErrorHTML,
  renderTokenFormHTML,
} from "./renderer";

export class WidgetController {
  private readonly config: WidgetEmbedConfig;
  private readonly apiClient: WidgetApiClient;
  private embed: WidgetEmbed | null = null;
  private brandConfig: WidgetBrandConfig | null = null;
  private currentLang: "en" | "es";
  private currentSummary: WidgetSummaryData | null = null;
  private langChangeHandler: ((event: Event) => void) | null = null;
  private tokenSubmitHandler: ((event: Event) => void) | null = null;

  constructor(config: WidgetEmbedConfig) {
    this.config = config;
    this.currentLang = config.lang;
    this.apiClient = new WidgetApiClient(config.apiBaseUrl);
  }

  async init(): Promise<void> {
    // Create iframe (shows loading spinner)
    this.embed = new WidgetEmbed(this.config);
    this.embed.mount();

    // Listen for language changes from iframe
    this.langChangeHandler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.lang) {
        this.handleLanguageChange(detail.lang);
      }
    };
    window.addEventListener("medicalnote:lang-change", this.langChangeHandler);

    // Listen for token submissions from iframe form
    this.tokenSubmitHandler = (event: Event) => {
      const detail = (event as CustomEvent).detail;
      if (detail?.token) {
        this.handleTokenSubmit(detail.token);
      }
    };
    window.addEventListener(
      "medicalnote:token-submit",
      this.tokenSubmitHandler
    );

    // Fetch widget branding config
    try {
      this.brandConfig = await this.apiClient.fetchWidgetConfig(
        this.config.widgetKey
      );
    } catch (error) {
      this.showError(
        error instanceof WidgetApiError ? error.code : "UNKNOWN_ERROR"
      );
      return;
    }

    // Check for token in URL hash (e.g., #token=abc123)
    const token = this.extractTokenFromURL();
    if (token) {
      await this.loadSummary(token);
    } else {
      this.showTokenForm();
    }
  }

  destroy(): void {
    if (this.langChangeHandler) {
      window.removeEventListener(
        "medicalnote:lang-change",
        this.langChangeHandler
      );
      this.langChangeHandler = null;
    }
    if (this.tokenSubmitHandler) {
      window.removeEventListener(
        "medicalnote:token-submit",
        this.tokenSubmitHandler
      );
      this.tokenSubmitHandler = null;
    }
    if (this.embed) {
      this.embed.destroy();
      this.embed = null;
    }
  }

  private async loadSummary(token: string): Promise<void> {
    if (!this.brandConfig || !this.embed) return;

    try {
      this.currentSummary = await this.apiClient.fetchSummary(token);
      this.renderSummary();

      // Mark as read (fire and forget)
      this.apiClient.markSummaryRead(token).catch(() => {
        // Silently ignore mark-read failures
      });
    } catch (error) {
      this.showError(
        error instanceof WidgetApiError ? error.code : "UNKNOWN_ERROR"
      );
    }
  }

  private renderSummary(): void {
    if (!this.brandConfig || !this.embed || !this.currentSummary) return;

    const themeVars = buildThemeVariables(this.brandConfig, this.config.theme);
    const html = renderSummaryHTML(
      this.currentSummary,
      this.brandConfig,
      themeVars,
      this.currentLang
    );
    this.embed.updateContent(html);
  }

  private showTokenForm(): void {
    if (!this.brandConfig || !this.embed) return;

    const themeVars = buildThemeVariables(this.brandConfig, this.config.theme);
    const html = renderTokenFormHTML(
      this.brandConfig,
      themeVars,
      this.currentLang
    );
    this.embed.updateContent(html);
  }

  private showError(errorCode: string): void {
    if (!this.embed) return;

    const themeVars = this.brandConfig
      ? buildThemeVariables(this.brandConfig, this.config.theme)
      : buildThemeVariables(
          {
            logo_url: "",
            brand_color: "",
            custom_domain: "",
            practice_name: "",
            widget_key: this.config.widgetKey,
          },
          this.config.theme
        );
    const html = renderErrorHTML(errorCode, themeVars, this.currentLang);
    this.embed.updateContent(html);
  }

  private handleLanguageChange(lang: "en" | "es"): void {
    this.currentLang = lang;
    if (this.currentSummary) {
      this.renderSummary();
    }
  }

  private async handleTokenSubmit(token: string): Promise<void> {
    await this.loadSummary(token);
  }

  private extractTokenFromURL(): string | null {
    const hash = window.location.hash;
    if (!hash) return null;

    const params = new URLSearchParams(hash.substring(1));
    return params.get("token");
  }
}
```

Run: `cd widget && npx vitest run src/__tests__/controller.test.ts`
Verify: All 5 tests pass.

---

## Chunk 10: Entry Point (index.ts)

### Task 10.1: Build the auto-initializing entry point

- [ ] **Step 1 (3 min):** Write failing tests.

File: `widget/src/__tests__/index.test.ts`
```ts
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
```

Run: `cd widget && npx vitest run src/__tests__/index.test.ts`
Verify: Tests fail.

- [ ] **Step 2 (4 min):** Implement the entry point.

File: `widget/src/index.ts`
```ts
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
  (window as Record<string, unknown>)["MedicalNoteWidget"] = {
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
```

Run: `cd widget && npx vitest run src/__tests__/index.test.ts`
Verify: All 5 tests pass.

---

## Chunk 11: Build Verification and Bundle Size Check

### Task 11.1: Build the widget and verify bundle size

- [ ] **Step 1 (3 min):** Run the full test suite.

```bash
cd widget && npx vitest run
```

Verify: All tests pass across all test files.

- [ ] **Step 2 (2 min):** Build the widget bundle.

```bash
cd widget && npx rollup -c
```

Verify: `widget/dist/widget.js` is created without errors.

- [ ] **Step 3 (2 min):** Check gzipped bundle size is under 50KB.

```bash
cd widget && gzip -c dist/widget.js | wc -c
```

Verify: Output is under 51200 bytes (50KB).

- [ ] **Step 4 (2 min):** Verify the bundle is a valid IIFE.

```bash
cd widget && head -1 dist/widget.js
```

Verify: Output starts with something like `var MedicalNoteWidget=(function(){` or similar IIFE pattern.

---

## Chunk 12: Example HTML File for Manual Testing

### Task 12.1: Create an example embed page

- [ ] **Step 1 (3 min):** Create a test HTML file.

File: `widget/examples/index.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MedicalNote Widget - Test Page</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
    }
    h1 { margin-bottom: 8px; }
    p { color: #666; margin-bottom: 24px; }
    .widget-container {
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      overflow: hidden;
    }
  </style>
</head>
<body>
  <h1>MedicalNote Widget - Integration Test</h1>
  <p>This page simulates a clinic's website embedding the MedicalNote widget.</p>

  <div class="widget-container">
    <div id="medicalnote-widget"></div>
  </div>

  <!-- Use local build for testing -->
  <script src="../dist/widget.js"
    data-widget-key="wk_test123"
    data-theme="light"
    data-lang="en"
    data-api-url="http://localhost:8000">
  </script>
</body>
</html>
```

- [ ] **Step 2 (2 min):** Create a dark mode variant.

File: `widget/examples/dark.html`
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MedicalNote Widget - Dark Mode Test</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 0 20px;
      background-color: #1a1a2e;
      color: #e0e0e0;
    }
    h1 { margin-bottom: 8px; }
    p { color: #999; margin-bottom: 24px; }
    .widget-container {
      border: 1px solid #374151;
      border-radius: 8px;
      overflow: hidden;
    }
  </style>
</head>
<body>
  <h1>MedicalNote Widget - Dark Mode</h1>
  <p>Testing the dark theme variant.</p>

  <div class="widget-container">
    <div id="medicalnote-widget"></div>
  </div>

  <script src="../dist/widget.js"
    data-widget-key="wk_test123"
    data-theme="dark"
    data-lang="es"
    data-api-url="http://localhost:8000">
  </script>
</body>
</html>
```

---

## Chunk 13: CDN Deployment Configuration

### Task 13.1: Create the S3/CloudFront deployment script

- [ ] **Step 1 (3 min):** Create a deployment script.

File: `widget/scripts/deploy.sh`
```bash
#!/bin/bash
set -euo pipefail

VERSION="${1:-v1}"
S3_BUCKET="medicalnote-widget-cdn"
DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:?Missing CLOUDFRONT_DISTRIBUTION_ID env var}"

echo "==> Building widget..."
cd "$(dirname "$0")/.."
npm run build

echo "==> Checking bundle size..."
BUNDLE_SIZE=$(gzip -c dist/widget.js | wc -c | tr -d '[:space:]')
MAX_SIZE=51200
if [ "$BUNDLE_SIZE" -gt "$MAX_SIZE" ]; then
  echo "ERROR: Bundle size ${BUNDLE_SIZE} bytes exceeds ${MAX_SIZE} bytes (50KB gzipped)"
  exit 1
fi
echo "    Bundle size: ${BUNDLE_SIZE} bytes gzipped (limit: ${MAX_SIZE})"

echo "==> Deploying to S3: s3://${S3_BUCKET}/${VERSION}/"
aws s3 cp dist/widget.js "s3://${S3_BUCKET}/${VERSION}/widget.js" \
  --content-type "application/javascript" \
  --cache-control "public, max-age=31536000, immutable" \
  --metadata-directive REPLACE

aws s3 cp dist/widget.js.map "s3://${S3_BUCKET}/${VERSION}/widget.js.map" \
  --content-type "application/json" \
  --cache-control "public, max-age=31536000, immutable" \
  --metadata-directive REPLACE

echo "==> Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/${VERSION}/*"

echo "==> Deployed widget ${VERSION} successfully!"
echo "    URL: https://widget.medicalnote.app/${VERSION}/widget.js"
```

- [ ] **Step 2 (2 min):** Make deploy script executable.

```bash
chmod +x widget/scripts/deploy.sh
```

---

## Chunk 14: Full Integration Test

### Task 14.1: End-to-end integration test

- [ ] **Step 1 (5 min):** Write an integration test that simulates the full widget lifecycle.

File: `widget/src/__tests__/integration.test.ts`
```ts
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { WidgetBrandConfig, WidgetSummaryData } from "../types";

describe("Widget Integration", () => {
  let container: HTMLDivElement;
  let scriptTag: HTMLScriptElement;

  const mockBrandConfig: WidgetBrandConfig = {
    logo_url: "https://cdn.example.com/logo.png",
    brand_color: "#FF5733",
    custom_domain: "",
    practice_name: "Acme Health Clinic",
    widget_key: "wk_integration",
  };

  const mockSummary: WidgetSummaryData = {
    id: "uuid-integration",
    summary_en:
      "You visited Dr. Jones today for a routine checkup. Your vital signs were all within normal range. Your blood pressure was 120/80, which is considered normal.",
    summary_es:
      "Visitaste al Dr. Jones hoy para un chequeo de rutina. Todos sus signos vitales estaban dentro del rango normal. Su presion arterial fue 120/80, lo cual es considerado normal.",
    reading_level: "grade_8",
    medical_terms_explained: [
      {
        term: "blood pressure",
        explanation:
          "the force of blood pushing against the walls of your arteries",
      },
      {
        term: "vital signs",
        explanation:
          "basic body measurements like temperature, heart rate, and blood pressure",
      },
    ],
    disclaimer_text:
      "This summary is for informational purposes only and does not constitute medical advice. Please contact your healthcare provider with any questions.",
    encounter_date: "2026-03-15",
    doctor_name: "Dr. Sarah Jones",
    delivery_status: "sent",
    viewed_at: null,
    created_at: "2026-03-15T14:30:00Z",
  };

  beforeEach(() => {
    container = document.createElement("div");
    container.id = "medicalnote-widget";
    document.body.appendChild(container);
    vi.restoreAllMocks();
  });

  afterEach(() => {
    document.body.innerHTML = "";
    vi.restoreAllMocks();
    delete (window as Record<string, unknown>)["MedicalNoteWidget"];
  });

  it("full lifecycle: init -> load config -> show form -> submit token -> show summary -> switch language", async () => {
    // Mock API calls in order: config, summary, mark-read
    const fetchMock = vi.spyOn(globalThis, "fetch");
    fetchMock
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockBrandConfig),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockSummary),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: "viewed" }),
      } as Response);

    // 1. Create controller and init
    const { WidgetController } = await import("../controller");
    const controller = new WidgetController({
      widgetKey: "wk_integration",
      theme: "light",
      lang: "en",
      apiBaseUrl: "https://api.medicalnote.app",
      containerId: "medicalnote-widget",
    });

    await controller.init();

    // 2. Verify iframe exists
    const iframe = container.querySelector("iframe");
    expect(iframe).not.toBeNull();

    // 3. Verify token form is shown (since no token in URL)
    let srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Access Code");
    expect(srcdoc).toContain("Acme Health Clinic");

    // 4. Simulate token submission via custom event
    window.dispatchEvent(
      new CustomEvent("medicalnote:token-submit", {
        detail: { token: "signed-token-integration" },
      })
    );

    // Wait for async operations
    await new Promise((resolve) => setTimeout(resolve, 50));

    // 5. Verify summary is displayed
    srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Dr. Sarah Jones");
    expect(srcdoc).toContain("routine checkup");
    expect(srcdoc).toContain("blood pressure");
    expect(srcdoc).toContain("vital signs");
    expect(srcdoc).toContain("informational purposes only");

    // 6. Verify API calls were made
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/widget/config/wk_integration/"),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/widget/summary/signed-token-integration/"),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining(
        "/widget/summary/signed-token-integration/read/"
      ),
      expect.anything()
    );

    // 7. Switch to Spanish
    window.dispatchEvent(
      new CustomEvent("medicalnote:lang-change", {
        detail: { lang: "es" },
      })
    );

    srcdoc = iframe?.getAttribute("srcdoc") || "";
    expect(srcdoc).toContain("Visitaste al Dr. Jones");
    expect(srcdoc).toContain("Resumen de la Visita");

    // 8. Clean up
    controller.destroy();
    expect(container.querySelector("iframe")).toBeNull();
  });
});
```

Run: `cd widget && npx vitest run src/__tests__/integration.test.ts`
Verify: Integration test passes.

- [ ] **Step 2 (2 min):** Run full test suite with coverage.

```bash
cd widget && npx vitest run --coverage
```

Verify: All tests pass. Coverage is above 80% on all metrics.

- [ ] **Step 3 (2 min):** Final build and size check.

```bash
cd widget && npm run build && npm run size
```

Verify: Build succeeds. Bundle is under 50KB gzipped.

---

## Summary of File Inventory

All files to create (21 files total):

**Config (4):** `widget/package.json`, `widget/tsconfig.json`, `widget/rollup.config.js`, `widget/vitest.config.ts`

**Source modules (8):** `widget/src/index.ts`, `widget/src/types.ts`, `widget/src/constants.ts`, `widget/src/api.ts`, `widget/src/theme.ts`, `widget/src/i18n.ts`, `widget/src/renderer.ts`, `widget/src/embed.ts`, `widget/src/controller.ts`, `widget/src/styles.ts`

**Tests (8):** `widget/src/__tests__/types.test.ts`, `widget/src/__tests__/api.test.ts`, `widget/src/__tests__/theme.test.ts`, `widget/src/__tests__/i18n.test.ts`, `widget/src/__tests__/renderer.test.ts`, `widget/src/__tests__/styles.test.ts`, `widget/src/__tests__/embed.test.ts`, `widget/src/__tests__/controller.test.ts`, `widget/src/__tests__/index.test.ts`, `widget/src/__tests__/integration.test.ts`

**Examples (2):** `widget/examples/index.html`, `widget/examples/dark.html`

**Scripts (1):** `widget/scripts/deploy.sh`

**Build output (generated):** `widget/dist/widget.js`, `widget/dist/widget.js.map`

---

### Critical Files for Implementation

- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/widget/src/controller.ts` - Core orchestration logic that ties all modules together: API client, embed, theme, and renderer
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/widget/src/renderer.ts` - HTML generation with XSS protection, CSP meta tags, medical term tooltips, and i18n; the most complex rendering logic
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/widget/src/embed.ts` - iframe creation with sandbox attributes, postMessage communication, and auto-resize handling
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/widget/src/api.ts` - API client consuming the backend widget endpoints defined in the backend plan at `backend/apps/widget/views.py`
- `/Users/yemalin.godonou/Documents/works/tiko/medicalnote/docs/superpowers/specs/2026-03-15-phase1-architecture-design.md` - Architecture spec (Section 7: White-Label Widget Architecture, lines 844-876) defines the requirements and API contracts this SDK must implement