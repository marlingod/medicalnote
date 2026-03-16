import type { WidgetBrandConfig, WidgetSummaryData } from "./types";
export declare class WidgetApiError extends Error {
    readonly status: number;
    readonly code: string;
    constructor(message: string, status: number, code: string);
}
export declare class WidgetApiClient {
    private readonly baseUrl;
    constructor(baseUrl: string);
    fetchWidgetConfig(widgetKey: string): Promise<WidgetBrandConfig>;
    fetchSummary(token: string): Promise<WidgetSummaryData>;
    markSummaryRead(token: string): Promise<void>;
    private request;
}
