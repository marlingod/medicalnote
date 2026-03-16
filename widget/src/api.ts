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
