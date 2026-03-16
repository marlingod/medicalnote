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
