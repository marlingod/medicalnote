import type { WidgetEmbedConfig } from "./types";
export declare class WidgetEmbed {
    private readonly config;
    private iframe;
    private messageHandler;
    constructor(config: WidgetEmbedConfig);
    mount(): void;
    updateContent(html: string): void;
    setHeight(height: number): void;
    destroy(): void;
    private setupMessageListener;
}
