/**
 * A dashboard card for the thl integration: the weekly numbers of one disease,
 * or of the flu-like illness visits, drawn on a map of Finland. Each wellbeing
 * services county is coloured by how it compares with the whole country, or by
 * how its cases changed from the week before. Clicking a county shows its own
 * figures and trend under the map.
 */
import { LitElement, css, html, nothing, svg } from "lit";
import type { CSSResultGroup, PropertyValues, TemplateResult } from "lit";
import { property, state } from "lit/decorators.js";
import { ifDefined } from "lit/directives/if-defined.js";

import {
    caseCount,
    changeText,
    FALLING,
    FALLING_FAST,
    fillColor,
    findArea,
    isVisits,
    NO_CASES,
    RISING,
    RISING_FAST,
    STEADY,
} from "./areas";
import { cardEntities } from "./editor";
import { CARD_VERSION, WHOLE_COUNTRY } from "./const";
import type { HomeAssistant } from "./hass";
import { gridMinRows, heightCardSize, heightStyle, validHeight } from "./height";
import { browserLanguage, translate } from "./localize/localize";
import { DISEASE_LOGO } from "./logos";
import { COUNTIES, MAP_GROUP_TRANSFORM, MAP_HEIGHT, MAP_VIEW_BOX, MAP_WIDTH, OUTLINES } from "./map/counties";
import type { CountyShape, Outline } from "./map/counties";
import { CAPITAL_REGION, COUNTY_LABELS, INSET_COUNTIES, INSET_VIEW_BOX, WITHOUT_INSET } from "./map/labels";
import { fetchTrend, fetchYearAgo, withCurrent } from "./trend";
import type { TrendPoint } from "./trend";
import type { Area, ColorBy, ThlCardConfig } from "./types";

/** The trend covers six months. */
const TREND_WEEKS = 26;
const [, , VIEW_WIDTH, VIEW_HEIGHT] = MAP_VIEW_BOX.split(" ").map(Number);
/** The capital region's frame on the map, around what the inset shows. */
const [FRAME_X, FRAME_Y, FRAME_WIDTH, FRAME_HEIGHT] = INSET_VIEW_BOX.split(" ").map(Number);

/** A trend that couldn't be fetched, such as while the websocket reconnects, is tried again after this long. */
const RETRY = 60 * 1000;

/**
 * The locales Home Assistant's number format setting asks for, as its own frontend reads it: `numberFormatToLocale`, except
 * none, which `formatNumberToParts` writes in en-US without grouping.
 */
function numberLocale(hass: HomeAssistant | undefined, language: string): string | string[] | undefined {
    switch (hass?.locale?.number_format) {
        case "comma_decimal":
            return ["en-US", "en"];
        case "decimal_comma":
            return ["de", "es", "it"];
        case "space_comma":
            return ["fr", "sv", "cs"];
        case "quote_decimal":
            return ["de-CH"];
        case "none":
            return "en-US";
        case "system":
            return undefined;
        default:
            return language;
    }
}

/** The space before a percent sign, in the languages that have one, as the frontend's `blankBeforePercent` has it. */
function blankBeforePercent(language: string): string {
    return ["cs", "de", "fi", "fr", "sk", "sv"].includes(language) ? " " : "";
}

interface CardRegistration {
    type: string;
    name: string;
    description: string;
    documentationURL?: string;
    preview?: boolean;
}

export class ThlCard extends LitElement {
    @property({ attribute: false }) public hass?: HomeAssistant;
    @property({ attribute: false }) public layout?: string;
    @state() private config?: ThlCardConfig;
    @state() private selected?: string;
    @state() private trend: TrendPoint[] = [];
    /** The point of the trend the pointer is over. */
    @state() private hovered?: number;
    /** Which of the configured sensors is shown, when there are several. */
    @state() private shown = 0;
    /** The chosen area's figure of the same week a year ago, when the statistics reach that far. */
    @state() private yearAgo?: number;
    /** What the trend shown was fetched for, so it is fetched again only when that changes. */
    private trendKey?: string;
    private yearAgoKey?: string;
    private retry?: number;

    public static getConfigElement(): HTMLElement {
        return document.createElement("thl-card-editor");
    }

    /** Offers the first disease of the thl integration when the card is added from the picker. */
    public static getStubConfig(hass?: HomeAssistant): Record<string, unknown> {
        return { entity: (hass ? cardEntities(hass)[0] : undefined) ?? "" };
    }

    public setConfig(config: ThlCardConfig): void {
        const entities = [config?.entity ?? []].flat().filter(Boolean);
        if (entities.length === 0) {
            throw new Error(translate(browserLanguage(), "invalid_configuration"));
        }
        if (!validHeight(config)) {
            throw new Error(translate(browserLanguage(), "invalid_height"));
        }
        // A changed list of sensors starts again from its first.
        if (this.config === undefined || String(entities) !== String(this.entities())) {
            this.shown = 0;
        }
        // The default county is chosen whenever the card loads or its configuration changes.
        if (this.config?.default_area !== config.default_area || this.config === undefined) {
            this.selected = config.default_area || undefined;
        }
        this.config = { ...config };
    }

    public getCardSize(): number {
        return heightCardSize(this.config ?? {}, 8, this.minimumHeight());
    }

    /** In a sections view the card is drawn full width, never squeezed below half a section, nor lower than its minimum. */
    public getGridOptions(): Record<string, unknown> {
        return { columns: 12, rows: "auto", min_columns: 6, min_rows: gridMinRows(this.minimumHeight()) };
    }

    public connectedCallback(): void {
        super.connectedCallback();
        // Back on the page, such as after a change of view: a fetch left waiting is tried now.
        if (this.hass && (this.trendKey === undefined || this.yearAgoKey === undefined)) {
            this.requestUpdate();
        }
    }

    public disconnectedCallback(): void {
        super.disconnectedCallback();
        // A fetch waiting to be tried again is tried when the card is shown again instead.
        if (this.retry !== undefined) {
            window.clearTimeout(this.retry);
            this.retry = undefined;
            this.trendKey = undefined;
            this.yearAgoKey = undefined;
        }
    }

    protected shouldUpdate(changed: PropertyValues): boolean {
        if ([...changed.keys()].some((key) => key !== "hass") || !this.config) {
            return true;
        }
        const previous = changed.get("hass") as HomeAssistant | undefined;
        // Redraw whenever a sensor itself changed, not only when the week did, and when the language or number format did.
        return (
            !previous ||
            this.entities().some((id) => previous.states[id] !== this.hass?.states[id]) ||
            previous.locale !== this.hass?.locale ||
            previous.language !== this.hass?.language
        );
    }

    protected render(): TemplateResult | typeof nothing {
        if (!this.hass || !this.config) {
            return nothing;
        }

        const entity = this.hass.states[this.sensorId()];
        if (!entity) {
            return this.message(this.text("entity_not_found", { entity: this.sensorId() }));
        }
        if (entity.state === "unavailable" || entity.state === "unknown") {
            return this.message(this.text("unavailable"));
        }

        const areas = (entity.attributes.values as Area[] | undefined) ?? [];
        const selected = this.selected === undefined ? undefined : findArea(areas, this.selected);
        const whole = findArea(areas, WHOLE_COUNTRY);
        const title = selected?.name ?? this.text("whole_country");
        const height = this.heightStyle();

        return html`
            <ha-card class=${height ? "held" : ""} style=${height}>
                <div class="card">
                    <div class="disease">
                        ${DISEASE_LOGO}
                        <span class="disease-name">${this.name(entity.attributes)}</span>
                    </div>
                    ${this.chips()}
                    <div class="content">
                        <div class="body">
                            ${this.map(areas, whole, height !== "")}
                            <div class="side">
                                <div class="figures">
                                    ${isVisits(areas) ? this.visits(title, selected ?? whole) : this.stats(title, selected ?? whole)}
                                </div>
                                ${this.showInset ? html`<div class="inset-room">${this.inset(areas, whole)}</div>` : nothing}
                            </div>
                        </div>
                        ${this.config.show_key === false ? nothing : this.key(areas)} ${this.trendLine()}
                    </div>
                </div>
            </ha-card>
        `;
    }

    protected updated(): void {
        void this.refreshTrend();
        void this.refreshYearAgo();
    }

    /** The configured sensors, one or several. */
    private entities(): string[] {
        return [this.config?.entity ?? []].flat().filter(Boolean);
    }

    private sensorId(): string {
        const entities = this.entities();
        return entities[Math.min(this.shown, entities.length - 1)] ?? "";
    }

    private get showInset(): boolean {
        return this.config?.show_inset !== false;
    }

    /** A button for each sensor when there are several, to switch between them. The chosen county stays chosen. */
    private chips(): TemplateResult | typeof nothing {
        const entities = this.entities();
        if (entities.length < 2) {
            return nothing;
        }
        return html`
            <div class="chips">
                ${entities.map((id, index) => {
                    const attributes = this.hass?.states[id]?.attributes;
                    return html`<button
                        class="chip ${index === this.shown ? "on" : ""}"
                        aria-pressed="${index === this.shown ? "true" : "false"}"
                        @click=${() => (this.shown = index)}
                    >
                        ${attributes ? this.name(attributes) : id}
                    </button>`;
                })}
            </div>
        `;
    }

    /** The disease, or the flu-like illness visits, which have no disease and go by their sensor's name. */
    private name(attributes: Record<string, unknown>): string {
        const disease = attributes.disease_name as string | undefined;
        return disease ?? String(attributes.friendly_name ?? "").replace(/^THL\s+/, "");
    }

    private get colorBy(): ColorBy {
        return this.config?.color_by ?? "level";
    }

    /** The map, in a room of its own that a card held to a height shrinks the map to fit, at a width the styles give it. */
    private map(areas: Area[], whole: Area | undefined, held: boolean): TemplateResult {
        const width = this.config?.map_width;
        const size =
            width === undefined || held
                ? `aspect-ratio: ${MAP_WIDTH} / ${MAP_HEIGHT};`
                : `aspect-ratio: ${MAP_WIDTH} / ${MAP_HEIGHT}; width: ${width}px; max-width: 100%;`;

        return html`
            <div class=${width === undefined ? "map-room" : "map-room sized"} style=${width === undefined ? "" : `--map-width: ${width}px`}>
                <div class="map" style="${size}">
                    ${COUNTY_LABELS.filter((label) => !(this.showInset && CAPITAL_REGION.includes(label.id))).map((label) => {
                        const at = (!this.showInset && WITHOUT_INSET[label.id]) || label;
                        const left = ((at.x / VIEW_WIDTH) * 100).toFixed(3);
                        const top = ((at.y / VIEW_HEIGHT) * 100).toFixed(3);
                        return html`<span class="amount" style="left: ${left}%; top: ${top}%;">${this.count(areas, label.id)}</span>`;
                    })}
                    <svg viewBox="${MAP_VIEW_BOX}" version="1.1" preserveAspectRatio="xMidYMid meet">
                        <g style="display:inline" transform="${MAP_GROUP_TRANSFORM}">
                            ${OUTLINES.filter((outline) => outline.layer === "under").map((outline) => this.outline(outline))}
                            ${COUNTIES.map((county) => this.county(county, areas, whole, true))} ${this.outlineOf(COUNTIES, true)}
                        </g>
                        <g style="display:inline" transform="${MAP_GROUP_TRANSFORM}">
                            ${OUTLINES.filter((outline) => outline.layer === "over").map((outline) => this.outline(outline))}
                        </g>
                        ${
                            this.showInset
                                ? svg`<rect class="frame" x="${FRAME_X}" y="${FRAME_Y}" width="${FRAME_WIDTH}" height="${FRAME_HEIGHT}" rx="6" />`
                                : nothing
                        }
                    </svg>
                </div>
            </div>
        `;
    }

    /**
     * The chosen county's outline, drawn after every county so its neighbours don't cover it. A copy of the shape, so
     * the counties keep their order and the one the keyboard is on stays the one it chose.
     */
    private outlineOf(counties: CountyShape[], onMap: boolean) {
        const county = counties.find((shape) => shape.id === this.selected);
        if (county === undefined) {
            return nothing;
        }
        const small = onMap && CAPITAL_REGION.includes(county.id) ? "small" : "";
        return svg`<path class="selected-outline ${small}" d="${county.d}" transform="${ifDefined(county.transform)}" />`;
    }

    /** A county on the map, which the keyboard reaches too, or its copy in the inset, which only the pointer does. */
    private county(county: CountyShape, areas: Area[], whole: Area | undefined, onMap: boolean) {
        const area = findArea(areas, county.id);
        return svg`<path
            d="${county.d}"
            transform="${ifDefined(county.transform)}"
            style="display:inline;fill:${fillColor(area, this.colorBy, whole)}"
            id="${ifDefined(onMap ? county.id : undefined)}"
            class="${this.selected === county.id ? "selected" : ""}"
            tabindex="${ifDefined(onMap ? "0" : undefined)}"
            role="${ifDefined(onMap ? "button" : undefined)}"
            aria-label="${ifDefined(onMap ? (area?.name ?? county.id) : undefined)}"
            aria-pressed="${ifDefined(onMap ? (this.selected === county.id ? "true" : "false") : undefined)}"
            @click="${() => this.select(county.id)}"
            @keydown="${(event: KeyboardEvent) => this.press(event, county.id)}"
        />`;
    }

    /**
     * The capital region again, larger, under the figures: Helsinki and Vantaa and Kerava are a few pixels each on
     * the map. The keyboard chooses them on the map, so the inset is hidden from it and from screen readers.
     */
    private inset(areas: Area[], whole: Area | undefined): TemplateResult {
        const counties = COUNTIES.filter((county) => INSET_COUNTIES.includes(county.id));
        return html`
            <div class="inset" aria-hidden="true">
                <svg viewBox="${INSET_VIEW_BOX}" preserveAspectRatio="xMidYMid meet">
                    <g transform="${MAP_GROUP_TRANSFORM}">
                        ${counties.map((county) => this.county(county, areas, whole, false))} ${this.outlineOf(counties, false)}
                    </g>
                </svg>
                ${COUNTY_LABELS.filter((label) => CAPITAL_REGION.includes(label.id)).map((label) => {
                    const left = (((label.x - FRAME_X) / FRAME_WIDTH) * 100).toFixed(2);
                    const top = (((label.y - FRAME_Y) / FRAME_HEIGHT) * 100).toFixed(2);
                    return html`<span class="amount" style="left: ${left}%; top: ${top}%;">${this.count(areas, label.id)}</span>`;
                })}
                <span class="inset-caption">${this.text("capital_region")}</span>
            </div>
        `;
    }

    /** What the colours mean, under the map: each colour's bound against the whole country, or of the change. */
    private key(areas: Area[]): TemplateResult {
        const change = this.colorBy === "change";
        const number = (value: number) => this.number(value, 2);
        const bounds = change
            ? [
                  number(0),
                  this.percent(-40, 2),
                  this.percent(-10, 2),
                  `±${this.percent(10, 2)}`,
                  `+${this.percent(10, 2)}`,
                  `+${this.percent(40, 2)}`,
              ]
            : [number(0), `< ${number(0.5)}`, `< ${number(0.8)}`, `≈ ${number(1)}`, `> ${number(1.25)}`, `> ${number(2)}`];
        const caption = change ? "key_change" : isVisits(areas) ? "key_share" : "key_level";
        return html`
            <div class="key">
                <div class="swatches">
                    ${[NO_CASES, FALLING_FAST, FALLING, STEADY, RISING, RISING_FAST].map((color) => html`<span style="background: ${color}"></span>`)}
                </div>
                <div class="bounds">${bounds.map((bound) => html`<span>${bound}</span>`)}</div>
                <span class="key-caption">${this.text(caption)}</span>
            </div>
        `;
    }

    private outline(outline: Outline) {
        return svg`<path id="${outline.id}" style="${outline.style}" d="${outline.d}" transform="${ifDefined(outline.transform)}" />`;
    }

    private stats(title: string, area: Area | undefined): TemplateResult | typeof nothing {
        if (area === undefined) {
            return nothing;
        }
        return html`
            <div class="stats-container">
                <span class="stats-title">${title}</span>
                <span class="stats">${this.text("last_week")}: ${this.number(area.amount_last_week ?? 0, 0)}</span>
                ${
                    area.incidence_last_week === undefined
                        ? nothing
                        : html`<span class="stats"
                              >${this.text("incidence")}: <span class="unit">${this.incidence(area.incidence_last_week)}</span></span
                          >`
                }
                ${
                    area.amount_two_weeks_ago === undefined
                        ? nothing
                        : html`<span class="stats">${this.text("two_weeks_ago")}: ${this.number(area.amount_two_weeks_ago, 0)}</span>`
                }
                ${
                    area.change_percentage === undefined
                        ? nothing
                        : html`<span class="stats">${this.text("change")}: ${this.change(area)}</span>`
                }
                ${this.yearAgo === undefined ? nothing : html`<span class="stats">${this.text("last_year")}: ${this.number(this.yearAgo, 0)}</span>`}
            </div>
        `;
    }

    /** The figures of the flu-like illness visits: their share of all visits, and how many there were. */
    private visits(title: string, area: Area | undefined): TemplateResult | typeof nothing {
        if (area === undefined) {
            return nothing;
        }
        const share = (value: number | null | undefined) => (value === null || value === undefined ? "–" : this.percent(value, 3));
        return html`
            <div class="stats-container">
                <span class="stats-title">${title}</span>
                <span class="stats">${this.text("last_week")}: ${share(area.share_last_week)}</span>
                ${
                    area.visits_last_week === undefined
                        ? nothing
                        : html`<span class="stats">
                              ${this.text("visits")}: ${this.number(area.visits_last_week, 0)} /
                              ${this.number(area.all_visits_last_week ?? 0, 0)}
                          </span>`
                }
                ${
                    area.share_two_weeks_ago === undefined
                        ? nothing
                        : html`<span class="stats">${this.text("two_weeks_ago")}: ${share(area.share_two_weeks_ago)}</span>`
                }
                ${this.yearAgo === undefined ? nothing : html`<span class="stats">${this.text("last_year")}: ${share(this.yearAgo)}</span>`}
            </div>
        `;
    }

    /** The chosen area's figure over the past weeks, as a line under its figures. Pointing at it shows a week. */
    private trendLine(): TemplateResult | typeof nothing {
        if (this.config?.show_trend === false || this.trend.length < 2) {
            return nothing;
        }
        const values = this.trend.map((point) => point.value);
        const highest = Math.max(...values);
        const top = highest > 0 ? highest : 1;
        const x = (index: number) => (index / (values.length - 1)) * 100;
        const y = (value: number) => 28 - (value / top) * 26;
        const points = values.map((value, index) => `${x(index).toFixed(2)},${y(value).toFixed(2)}`).join(" ");
        const digits = isVisits(this.areas()) ? 3 : 1;
        // A point of a trend that has since been replaced by a shorter one is the newest of the new.
        const marked = Math.min(this.hovered ?? values.length - 1, values.length - 1);
        // The dot and the bubble sit over the drawing, so the stretched line doesn't stretch them.
        const at = `left: ${x(marked).toFixed(2)}%; top: ${((y(values[marked]) / 30) * 100).toFixed(2)}%;`;
        const bubble = `${this.text("week_short")} ${this.number(this.trend[marked].week, 0)}: ${this.number(values[marked], digits)}`;

        return html`
            <div class="trend">
                <div
                    class="trend-plot"
                    tabindex="0"
                    @pointerdown=${(event: PointerEvent) => this.hover(event)}
                    @pointermove=${(event: PointerEvent) => this.hover(event)}
                    @pointerleave=${(event: PointerEvent) => this.leave(event)}
                    @keydown=${(event: KeyboardEvent) => this.step(event)}
                    @blur=${() => (this.hovered = undefined)}
                >
                    <svg viewBox="0 0 100 30" preserveAspectRatio="none" role="img" aria-label="${this.text("trend")}">
                        <polyline class="trend-area" points="0,30 ${points} 100,30" />
                        <polyline class="trend-line" points="${points}" vector-effect="non-scaling-stroke" />
                    </svg>
                    <span class="trend-dot ${this.hovered === undefined ? "" : "hovered"}" style="${at}"></span>
                    ${
                        this.hovered === undefined
                            ? nothing
                            : html`<span class="trend-bubble" style="left: ${x(marked).toFixed(2)}%;">${bubble}</span>`
                    }
                </div>
                <span class="trend-caption">
                    ${this.text("trend_caption", { weeks: this.number(values.length, 0) })} · ${this.text("highest")}
                    ${this.number(highest, digits)}
                </span>
            </div>
        `;
    }

    private hover(event: PointerEvent): void {
        const plot = event.currentTarget as HTMLElement;
        const box = plot.getBoundingClientRect();
        if (box.width === 0 || this.trend.length < 2) {
            return;
        }
        const fraction = Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1);
        this.hovered = Math.round(fraction * (this.trend.length - 1));
    }

    /** A touch ends with the finger leaving, so the week it showed stays until the next touch. */
    private leave(event: PointerEvent): void {
        if (event.pointerType !== "touch") {
            this.hovered = undefined;
        }
    }

    /** The arrow keys move along the trend, Home and End to its ends. */
    private step(event: KeyboardEvent): void {
        const last = this.trend.length - 1;
        const current = this.hovered ?? last;
        const next = { ArrowLeft: current - 1, ArrowRight: current + 1, Home: 0, End: last }[event.key];
        if (next !== undefined) {
            event.preventDefault();
            this.hovered = Math.min(Math.max(next, 0), last);
        }
    }

    private press(event: KeyboardEvent, id: string): void {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            this.select(id);
        }
    }

    /**
     * The sensor the trend is drawn from and the figure it shows now: the level for colouring by level, the cases
     * otherwise. A county of the flu-like illness visits has one sensor, its share.
     */
    private trendSource(): { id: string; value: number | undefined } | undefined {
        const area = findArea(this.areas(), this.selected ?? WHOLE_COUNTRY);
        if (area === undefined) {
            return undefined;
        }
        if (this.colorBy === "level" && area.incidence_entity_id && area.incidence_last_week !== undefined) {
            return { id: area.incidence_entity_id, value: area.incidence_last_week };
        }
        if (!area.entity_id) {
            return undefined;
        }
        const value = isVisits(this.areas()) ? area.share_last_week : area.amount_last_week;
        return { id: area.entity_id, value: value ?? undefined };
    }

    private async refreshTrend(): Promise<void> {
        if (!this.hass || !this.config || this.config.show_trend === false) {
            return;
        }
        const source = this.trendSource();
        const week = Number(this.hass.states[this.sensorId()]?.attributes.last_week);
        // The figure is part of it, as THL may correct the week it has published.
        const key = `${source?.id}|${week}|${source?.value}`;
        if (key === this.trendKey) {
            return;
        }
        this.trendKey = key;
        this.hovered = undefined;
        if (source === undefined) {
            this.trend = [];
            return;
        }
        try {
            const points = await fetchTrend(this.hass, source.id, TREND_WEEKS);
            // A newer request may have been made while this one was on its way.
            if (this.trendKey === key) {
                this.trend = withCurrent(points, Number.isFinite(week) ? week : undefined, source.value, TREND_WEEKS);
            }
        } catch {
            if (this.trendKey === key) {
                this.trend = [];
                this.retryLater();
            }
        }
    }

    /**
     * Tries the fetches again after a while, such as once the websocket has reconnected. The keys stay until then, so
     * drawing what is left doesn't ask again straight away.
     */
    private retryLater(): void {
        window.clearTimeout(this.retry);
        this.retry = window.setTimeout(() => {
            this.retry = undefined;
            this.trendKey = undefined;
            this.yearAgoKey = undefined;
            this.requestUpdate();
        }, RETRY);
    }

    /** The chosen area's figure of the same week a year ago: its cases, or its share of visits. */
    private async refreshYearAgo(): Promise<void> {
        if (!this.hass || !this.config) {
            return;
        }
        const area = findArea(this.areas(), this.selected ?? WHOLE_COUNTRY);
        const week = Number(this.hass.states[this.sensorId()]?.attributes.last_week);
        const key = `${area?.entity_id}|${week}`;
        if (key === this.yearAgoKey) {
            return;
        }
        this.yearAgoKey = key;
        this.yearAgo = undefined;
        if (!area?.entity_id || !Number.isFinite(week)) {
            return;
        }
        try {
            const value = await fetchYearAgo(this.hass, area.entity_id, week);
            if (this.yearAgoKey === key) {
                this.yearAgo = value;
            }
        } catch {
            if (this.yearAgoKey === key) {
                this.retryLater();
            }
        }
    }

    /** A county's number on the map, written as the user's number format writes it. */
    private count(areas: Area[], id: string): string {
        const count = caseCount(areas, id);
        return typeof count === "number" ? this.number(count, 0) : count;
    }

    private areas(): Area[] {
        const entity = this.config ? this.hass?.states[this.sensorId()] : undefined;
        return (entity?.attributes.values as Area[] | undefined) ?? [];
    }

    /** Cases per 100 000 people. */
    private incidence(value: number): string {
        return `${this.number(value, 1)} / ${this.number(100000, 0)}`;
    }

    /** The change from the week before, as a percentage and in cases. */
    private change(area: Area): string {
        return `${changeText(area, (value) => this.percent(value, 0))} (${this.number(area.change_in_numbers ?? 0, 0)})`;
    }

    private percent(value: number, digits: number): string {
        return `${this.number(value, digits)}${blankBeforePercent(this.language())}%`;
    }

    private number(value: number, digits: number): string {
        const grouping = this.hass?.locale?.number_format === "none" ? false : undefined;
        return new Intl.NumberFormat(numberLocale(this.hass, this.language()), {
            maximumFractionDigits: digits,
            useGrouping: grouping,
        }).format(value);
    }

    private message(text: string): TemplateResult {
        return html`<ha-card style=${this.heightStyle()}><div class="message">${text}</div></ha-card>`;
    }

    private heightStyle(): string {
        return heightStyle(this.config ?? {}, this.layout, this.minimumHeight());
    }

    private select(id: string): void {
        // Clicking the county that is already chosen goes back to the whole country.
        this.selected = this.selected === id ? undefined : id;
    }

    private text(key: string, replacements?: Record<string, string>): string {
        return translate(this.language(), key, replacements);
    }

    /**
     * The lowest the card is held to, in pixels: its padding, the disease, the buttons when there are several sensors,
     * a map 200 px high (or lower, when its width is set to less), the key and the trend, each when it is shown, as
     * measured on a full section's width. A lower map no longer shows the regions or the capital region's inset. Set
     * narrower than a full section, the card may be under 290 px wide, in a view of four sections, where the figures go
     * under the map instead of over its sea, so they are counted too. The columns are read as Home Assistant reads them:
     * `grid_options.columns` when there are grid options, otherwise the older `layout_options.grid_columns`, a third as
     * many.
     */
    private minimumHeight(): number {
        const padding = 24;
        const gap = 12;
        const disease = 34;
        const chips = 22;
        const map = Math.min(200, ((this.config?.map_width ?? Infinity) * MAP_HEIGHT) / MAP_WIDTH);
        const key = 36;
        const trend = 55;
        const figures = 86;
        const older = (this.config?.layout_options as { grid_columns?: unknown } | undefined)?.grid_columns;
        const columns = this.config?.grid_options
            ? (this.config.grid_options as { columns?: unknown }).columns
            : typeof older === "number"
              ? older * 3
              : undefined;
        const narrow = typeof columns === "number" && columns < 12;
        return (
            padding +
            disease +
            (this.entities().length > 1 ? gap + chips : 0) +
            gap +
            map +
            (narrow ? gap + figures : 0) +
            (this.config?.show_key === false ? 0 : gap + key) +
            (this.config?.show_trend === false ? 0 : gap + trend)
        );
    }

    private language(): string {
        return this.hass?.locale?.language ?? this.hass?.language ?? browserLanguage();
    }

    static get styles(): CSSResultGroup {
        return css`
            /* As tall as a sections view's grid rows make its cell, which a card held by them fills. */
            :host {
                display: block;
                height: 100%;
            }

            ha-card {
                container: thl / inline-size;
            }

            .card,
            .content {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
            }

            .card {
                container-type: inline-size;
                padding: 12px;
                box-sizing: border-box;
            }

            .content {
                width: 100%;
            }

            /*
             * Held to a height, by its height mode or a sections view's rows, nothing scrolls, as a map scrolled out of
             * view is no use. The disease and its buttons stay at the top, the key and the trend whole under the map,
             * and the map shrinks to the height left between them, never below 200 px. Its room is a size container,
             * as only a height the map's width can be worked out from lets it keep its shape. Unheld, the room is no
             * box at all, and the card looks as it always has.
             */
            ha-card.held {
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            ha-card.held .card {
                flex: 1 1 auto;
                min-height: 0;
            }

            ha-card.held .card > *,
            ha-card.held .content > *,
            ha-card.held .body > * {
                flex: none;
            }

            ha-card.held .card > .content,
            ha-card.held .content > .body {
                flex: 0 1 auto;
                min-height: 0;
            }

            .map-room,
            .inset-room {
                display: contents;
            }

            /* As tall as the map would be unheld, as the room's size can't come from the map inside it. */
            ha-card.held .body > .map-room {
                --natural: calc(min(var(--map-width, 300px), 100cqw) * ${MAP_HEIGHT} / ${MAP_WIDTH});
                display: flex;
                flex: 0 1 auto;
                align-self: stretch;
                align-items: center;
                justify-content: center;
                container-type: size;
                height: var(--natural);
                min-height: min(200px, var(--natural));
            }

            ha-card.held .map {
                width: min(var(--map-width, 300px), 100cqw, 100cqh * ${MAP_WIDTH} / ${MAP_HEIGHT});
            }

            /* The disease is named at the top, on one line whatever width the card has. */
            .disease {
                display: flex;
                align-items: center;
                justify-content: center;
                /* The drawing and the gap are sized from this, so the whole row keeps its proportions at every width. */
                font-size: clamp(11px, 5.5cqw, 18px);
                gap: 0.5em;
                max-width: 100%;
                max-height: 48px;
            }

            .disease-logo {
                flex: 0 0 auto;
                width: 1.7em;
                height: 1.7em;
            }

            .disease-name {
                min-width: 0;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                font-weight: 600;
            }

            .map {
                position: relative;
                container-type: inline-size;
                /* Grows with the card, but only so far: taller than this and it swamps the page. */
                width: min(100%, 300px);
            }

            .map svg {
                display: block;
                width: 100%;
                height: 100%;
            }

            .map path {
                cursor: pointer;
            }

            .map path:hover {
                opacity: 0.7;
            }

            .map path:active {
                opacity: 0.4;
            }

            /* The chosen county keeps its colour, which means something, and gets an outline instead. */
            .selected-outline {
                fill: none;
                stroke: var(--primary-text-color);
                stroke-width: 2.5px;
                vector-effect: non-scaling-stroke;
                pointer-events: none;
            }

            /* On the map the capital region's counties are too small for a thick line; the inset shows it. */
            .selected-outline.small {
                stroke-width: 1px;
            }

            .map path:focus {
                outline: none;
            }

            .map path:focus-visible {
                stroke: var(--primary-color);
                stroke-width: 3px;
                vector-effect: non-scaling-stroke;
            }

            /* Each number is centred on its county, in dark text, which reads on every colour of the map in both themes. */
            .amount {
                position: absolute;
                transform: translate(-50%, -50%);
                color: #1a1a1a;
                font-weight: 600;
                /* The numbers lie on top of the shapes, so let the clicks through to the county beneath. */
                pointer-events: none;
                /* 8.5px when the map is its original 235px wide, and in proportion after that, but never too small to read. */
                font-size: 8.5px;
                font-size: max(7.5px, 3.6cqw);
                white-space: nowrap;
            }

            .frame {
                fill: none;
                stroke: var(--secondary-text-color);
                stroke-width: 1px;
                stroke-dasharray: 3 2;
                vector-effect: non-scaling-stroke;
                pointer-events: none;
            }

            .inset {
                position: relative;
                container-type: inline-size;
                flex: 0 0 auto;
                width: 112px;
                border: 1px dashed var(--secondary-text-color);
                border-radius: 6px;
                overflow: hidden;
            }

            .inset svg {
                display: block;
                width: 100%;
                height: auto;
            }

            .inset path {
                cursor: pointer;
            }

            .inset path:hover {
                opacity: 0.7;
            }

            .inset .amount {
                font-size: 11px;
            }

            .inset-caption {
                position: absolute;
                inset: 0 0 auto;
                padding: 1px 0;
                text-align: center;
                /* Smaller in a small inset, so the name fits. */
                font-size: min(10px, 11cqw);
                white-space: nowrap;
                color: var(--secondary-text-color);
                background: color-mix(in srgb, var(--card-background-color, #fff) 85%, transparent);
                pointer-events: none;
            }

            .key {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px;
                width: min(100%, 300px);
                font-size: 10px;
                color: var(--secondary-text-color);
            }

            .swatches,
            .bounds {
                display: flex;
                width: 100%;
            }

            .swatches {
                height: 8px;
                border-radius: 4px;
                overflow: hidden;
            }

            .swatches span,
            .bounds span {
                flex: 1;
                text-align: center;
                white-space: nowrap;
            }

            /* No cases at all is a colour of its own, apart from the scale. */
            .swatches span:first-child,
            .bounds span:first-child {
                margin-right: 3px;
            }

            .chips {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 6px;
            }

            .chip {
                font: inherit;
                font-size: 12px;
                padding: 3px 10px;
                border-radius: 14px;
                border: 1px solid var(--divider-color, rgba(0, 0, 0, 0.12));
                background: none;
                color: var(--primary-text-color);
                cursor: pointer;
            }

            .chip.on {
                background: var(--primary-color);
                border-color: var(--primary-color);
                color: var(--text-primary-color, #fff);
            }

            .figures {
                display: flex;
                justify-content: center;
                width: 100%;
            }

            .stats-container {
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
            }

            /* A figure and its unit stay on one line. */
            .unit {
                white-space: nowrap;
            }

            .stats-title {
                font-weight: 600;
            }

            .stats {
                font-size: 12px;
            }

            .body {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 12px;
                width: 100%;
            }

            /* The figures, and the inset under them. */
            .side {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                align-items: center;
                gap: 12px 20px;
                width: 100%;
            }

            .trend {
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 2px;
                width: min(100%, 300px);
            }

            .trend-plot {
                position: relative;
                width: 100%;
                height: 40px;
                cursor: crosshair;
                /* A finger drawn sideways moves along the trend, up and down it still scrolls the page. */
                touch-action: pan-y;
                border-radius: 4px;
            }

            .trend-plot:focus {
                outline: none;
            }

            .trend-plot:focus-visible {
                outline: 2px solid var(--primary-color);
                outline-offset: 4px;
            }

            .trend svg {
                display: block;
                width: 100%;
                height: 100%;
                overflow: visible;
            }

            .trend-dot {
                position: absolute;
                width: 6px;
                height: 6px;
                margin: -3px 0 0 -3px;
                border-radius: 50%;
                background: var(--primary-color);
                pointer-events: none;
            }

            .trend-dot.hovered {
                width: 8px;
                height: 8px;
                margin: -4px 0 0 -4px;
                box-shadow: 0 0 0 2px var(--card-background-color, #fff);
            }

            .trend-bubble {
                position: absolute;
                bottom: calc(100% + 4px);
                transform: translateX(-50%);
                padding: 2px 6px;
                border-radius: 4px;
                background: var(--primary-text-color);
                color: var(--card-background-color, #fff);
                font-size: 11px;
                white-space: nowrap;
                pointer-events: none;
            }

            .trend-line {
                fill: none;
                stroke: var(--primary-color);
                stroke-width: 2;
                stroke-linejoin: round;
            }

            .trend-area {
                fill: var(--primary-color);
                opacity: 0.15;
                stroke: none;
            }

            .trend-caption {
                font-size: 11px;
                color: var(--secondary-text-color);
            }

            /*
             * Narrower, held to a height, the inset under the figures shrinks with the map, in a size container of its own
             * as the map's is. Its 2 px are the inset's border. Without the inset nothing under the map can shrink.
             */
            @container thl not (min-width: 290px) {
                ha-card.held .body > .side:has(> .inset-room) {
                    flex: 0 1 auto;
                    flex-direction: column;
                    flex-wrap: nowrap;
                    justify-content: flex-start;
                    min-height: 0;
                }

                ha-card.held .side > .figures {
                    flex: none;
                }

                ha-card.held .side > .inset-room {
                    --natural: calc(112px * ${FRAME_HEIGHT} / ${FRAME_WIDTH} + 2px);
                    display: flex;
                    flex: 0 1 auto;
                    align-self: stretch;
                    justify-content: center;
                    container-type: size;
                    height: var(--natural);
                    min-height: 0;
                }

                ha-card.held .inset-room .inset {
                    width: min(112px, (100cqh - 2px) * ${FRAME_WIDTH} / ${FRAME_HEIGHT});
                }
            }

            /* From a whole section of four in a view on down to a third of one of two: the map to the right, the figures over
               the sea west of it, so the card isn't taller than it needs to be. Narrower, the figures stay under the map. */
            @container thl (min-width: 290px) {
                /* However wide the card, the map and the figures stay together in the middle. */
                .body,
                .trend,
                .key {
                    width: 100%;
                    max-width: 560px;
                }

                .body {
                    position: relative;
                    align-items: flex-end;
                }

                .map {
                    width: min(68%, 300px);
                }

                .side {
                    position: absolute;
                    left: 0;
                    top: 16%;
                    bottom: 0;
                    width: 50%;
                    flex-direction: column;
                    flex-wrap: nowrap;
                    justify-content: flex-start;
                    align-items: flex-start;
                    /* Only the figures take the pointer; the counties under the rest stay clickable. */
                    pointer-events: none;
                }

                .side > * {
                    pointer-events: auto;
                }

                .card {
                    padding: 12px 16px;
                }

                /* The map keeps to the right, where the figures over the sea west of it leave it room. */
                ha-card.held .body > .map-room {
                    --natural: calc(min(68 * min(100cqw, 560px) / 100, 300px) * ${MAP_HEIGHT} / ${MAP_WIDTH});
                    justify-content: flex-end;
                }

                ha-card.held .body > .map-room.sized {
                    --natural: calc(min(var(--map-width), 100cqw, 560px) * ${MAP_HEIGHT} / ${MAP_WIDTH});
                }

                ha-card.held .map {
                    width: min(68cqw, 300px, 100cqh * ${MAP_WIDTH} / ${MAP_HEIGHT});
                }

                ha-card.held .map-room.sized .map {
                    width: min(var(--map-width), 100cqw, 100cqh * ${MAP_WIDTH} / ${MAP_HEIGHT});
                }

                /*
                 * The inset shrinks with the map, in the room the figures leave it in the column beside the map, so it
                 * never reaches over the key. Its room is a size container for the same reason as the map's.
                 */
                ha-card.held .side > .inset-room {
                    --natural: calc(clamp(84px, 30 * min(100cqw, 560px) / 100, 140px) * ${FRAME_HEIGHT} / ${FRAME_WIDTH});
                    display: flex;
                    flex: 0 1 auto;
                    align-self: stretch;
                    align-items: flex-end;
                    container-type: size;
                    margin-top: auto;
                    height: var(--natural);
                    min-height: 0;
                    pointer-events: none;
                }

                ha-card.held .inset-room .inset {
                    margin-top: 0;
                    pointer-events: auto;
                    width: min(clamp(84px, 60cqw, 140px), 100cqh * ${FRAME_WIDTH} / ${FRAME_HEIGHT});
                }

                .disease {
                    font-size: clamp(11px, 5.5cqw, 20px);
                }

                /* At the bottom of the column, clear of the map, which is to the right of it. */
                .inset {
                    margin-top: auto;
                    width: clamp(84px, 60%, 140px);
                }

                .figures {
                    justify-content: flex-start;
                }

                .stats-container {
                    align-items: flex-start;
                    text-align: left;
                }
            }

            .message {
                padding: 16px;
                color: var(--primary-text-color);
            }
        `;
    }
}

// Anyone who installed the card on its own before it came with the integration may still load that copy too, as a
// dashboard resource of its own. Whichever loads first is the card, and the other stays out of the way.
if (!customElements.get("thl-card")) {
    console.info(
        `%c  THL-CARD  \n%c  ${CARD_VERSION}    `,
        "color: orange; font-weight: bold; background: black",
        "color: white; font-weight: bold; background: dimgray",
    );

    const registry = window as unknown as { customCards?: CardRegistration[] };
    registry.customCards = registry.customCards ?? [];
    registry.customCards.push({
        type: "thl-card",
        name: translate(browserLanguage(), "name"),
        description: translate(browserLanguage(), "description"),
        documentationURL: "https://github.com/jesmak/thl#thl-card",
        preview: true,
    });
    customElements.define("thl-card", ThlCard);
}

declare global {
    interface HTMLElementTagNameMap {
        "thl-card": ThlCard;
    }
}
