import type { WidgetEmbedConfig } from "./types";
export declare class WidgetController {
    private readonly config;
    private readonly apiClient;
    private embed;
    private brandConfig;
    private currentLang;
    private currentSummary;
    private langChangeHandler;
    private tokenSubmitHandler;
    constructor(config: WidgetEmbedConfig);
    init(): Promise<void>;
    destroy(): void;
    private loadSummary;
    private renderSummary;
    private showTokenForm;
    private showError;
    private handleLanguageChange;
    private handleTokenSubmit;
    private extractTokenFromURL;
}
