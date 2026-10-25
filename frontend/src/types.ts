import type { LovelaceCardConfig } from "./hass";

/** `level` compares each county with the whole country; `change` with its own week before. */
export type ColorBy = "level" | "change";

export interface ThlCardConfig extends LovelaceCardConfig {
    /** The whole country's sensor of a disease, or several, which the card switches between with buttons over the map. */
    entity: string | string[];
    /** A fixed width for the map in pixels. Left out, the map follows the width of the card. */
    map_width?: number;
    /** How the counties are coloured. Left out, by level. */
    color_by?: ColorBy;
    /** The area_id of a county chosen whenever the card loads. Left out, the whole country. */
    default_area?: string;
    /** Whether a trend of the chosen area's past six months is drawn with its figures. Left out, it is. */
    show_trend?: boolean;
    /** Whether the capital region, too small to point at on the map, is drawn again larger. Left out, it is. */
    show_inset?: boolean;
    /** Whether a key under the map says what the colours mean. Left out, it does. */
    show_key?: boolean;
}

/**
 * One area, as the thl integration writes it into the whole country's sensor's `values`.
 *
 * A disease has the cases and incidence; the flu-like illness visits have the share and visits.
 */
export interface Area {
    area_id: string;
    name: string;
    amount_last_week?: number;
    /** All three are missing when THL hasn't published the week before. */
    amount_two_weeks_ago?: number;
    change_in_numbers?: number;
    /** A rounded string such as "-15", or the number 0 when there were no cases to compare with. */
    change_percentage?: string | number;
    /** Cases per 100 000 people. */
    incidence_last_week?: number;
    incidence_two_weeks_ago?: number;
    /** Flu-like illness visits as a percentage of all primary care visits. */
    share_last_week?: number | null;
    share_two_weeks_ago?: number | null;
    visits_last_week?: number;
    all_visits_last_week?: number;
    /** The area's own sensors, whose statistics the trend is drawn from. */
    entity_id?: string | null;
    incidence_entity_id?: string | null;
}
