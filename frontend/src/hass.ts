/** The little of Home Assistant a card needs, so the unmaintained custom-card-helpers isn't a dependency. */

export interface HassEntity {
    entity_id: string;
    state: string;
    attributes: Record<string, unknown>;
}

export interface HomeAssistant {
    states: Record<string, HassEntity | undefined>;
    language?: string;
    /** The user's profile settings: `number_format` is "language", "system", "comma_decimal", "decimal_comma", "space_comma", "quote_decimal" or "none". */
    locale?: { language?: string; number_format?: string };
    /** Home Assistant's websocket API, which the trend reads statistics from. */
    callWS?<T>(message: Record<string, unknown>): Promise<T>;
}

export interface LovelaceCardConfig {
    type: string;
    [key: string]: unknown;
}
