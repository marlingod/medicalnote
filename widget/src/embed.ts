import type { WidgetEmbedConfig } from "./types";
import { IFRAME_ID, MAX_IFRAME_HEIGHT, MIN_IFRAME_HEIGHT, MESSAGE_NAMESPACE } from "./constants";
import { renderLoadingHTML } from "./renderer";
import { buildThemeVariables } from "./theme";

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
    this.iframe.setAttribute("frameBorder", "0");
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
