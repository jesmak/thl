import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import "../src/thl-card";
import type { ThlCard } from "../src/thl-card";
import { FALLING_FAST, NO_CASES, NO_DATA, RISING_FAST } from "../src/areas";
import type { HomeAssistant } from "../src/hass";
import type { Area } from "../src/types";

const ENTITY = "sensor.thl_influenssa";

const AREAS: Area[] = [
    {
        area_id: "finland",
        name: "Kaikki hyvinvointialueet",
        amount_last_week: 17,
        amount_two_weeks_ago: 20,
        change_in_numbers: -3,
        change_percentage: "-15",
    },
    {
        area_id: "lapin_hyvinvointialue",
        name: "Lapin hyvinvointialue",
        amount_last_week: 2,
        amount_two_weeks_ago: 0,
        change_in_numbers: 2,
        change_percentage: 0,
    },
    {
        area_id: "ahvenanmaa",
        name: "Ahvenanmaa",
        amount_last_week: 0,
        amount_two_weeks_ago: 0,
        change_in_numbers: 0,
        change_percentage: 0,
    },
    {
        area_id: "kainuun_hyvinvointialue",
        name: "Kainuun hyvinvointialue",
        amount_last_week: 0,
        amount_two_weeks_ago: 9,
        change_in_numbers: -9,
        change_percentage: "-100",
    },
    {
        area_id: "pirkanmaan_hyvinvointialue",
        name: "Pirkanmaan hyvinvointialue",
        amount_last_week: 9,
        amount_two_weeks_ago: 2,
        change_in_numbers: 7,
        change_percentage: "350",
    },
];

function hass(overrides: Partial<{ state: string; values: Area[] }> = {}): HomeAssistant {
    return {
        locale: { language: "fi" },
        states: {
            [ENTITY]: {
                entity_id: ENTITY,
                state: overrides.state ?? "17",
                attributes: {
                    disease_name: "Influenssa",
                    last_week: 37,
                    values: overrides.values ?? AREAS,
                },
            },
        },
    };
}

async function card(state: HomeAssistant, config: Record<string, unknown> = { entity: ENTITY }): Promise<ThlCard> {
    const element = document.createElement("thl-card") as ThlCard;
    element.setConfig({ type: "custom:thl-card", ...config } as never);
    element.hass = state;
    document.body.append(element);
    await element.updateComplete;
    return element;
}

function shadow(element: ThlCard): ShadowRoot {
    const root = element.shadowRoot;
    if (!root) {
        throw new Error("the card rendered nothing");
    }
    return root;
}

beforeEach(() => {
    document.body.innerHTML = "";
});

describe("the map", () => {
    it("draws every county and both outlines", async () => {
        const root = shadow(await card(hass()));
        expect(root.querySelectorAll(".map svg path")).toHaveLength(25);
        expect(root.querySelector("#lapin_hyvinvointialue")).not.toBeNull();
        expect(root.querySelector("#ahvenanmaa")).not.toBeNull();
    });

    it("writes each county’s cases on the map", async () => {
        const root = shadow(await card(hass()));
        const labels = [...root.querySelectorAll(".amount")].map((span) => span.textContent?.trim());
        expect(labels).toHaveLength(23);
        expect(labels).toContain("2");
        // Counties the sensor carries no numbers for are left blank, not "undefined".
        expect(labels.filter((text) => text === "")).not.toHaveLength(0);
        expect(labels.some((text) => text?.includes("undefined"))).toBe(false);
    });

    it("colours counties by how their numbers changed", async () => {
        const root = shadow(await card(hass(), { entity: ENTITY, color_by: "change" }));
        const fill = (id: string) => root.querySelector(`#${id}`)?.getAttribute("style");
        expect(fill("kainuun_hyvinvointialue")).toContain(FALLING_FAST);
        expect(fill("pirkanmaan_hyvinvointialue")).toContain(RISING_FAST);
        expect(fill("ahvenanmaa")).toContain(NO_CASES);
        // A county the sensor doesn't carry at all.
        expect(fill("satakunnan_hyvinvointialue")).toContain(NO_DATA);
    });

    it("writes a dash for the change of a county that had no cases the week before", async () => {
        const element = await card(hass());
        (shadow(element).querySelector("#lapin_hyvinvointialue") as SVGElement).dispatchEvent(new Event("click"));
        await element.updateComplete;
        expect(shadow(element).querySelector(".stats-container")?.textContent?.replace(/\s+/g, " ")).toContain("Muutos: – (2)");
    });

    it("lets a county be chosen from the keyboard, and says which one is chosen", async () => {
        const element = await card(hass());
        const lapland = shadow(element).querySelector("#lapin_hyvinvointialue") as SVGElement;
        expect(lapland.getAttribute("tabindex")).toBe("0");
        expect(lapland.getAttribute("aria-label")).toBe("Lapin hyvinvointialue");
        expect(lapland.getAttribute("aria-pressed")).toBe("false");

        lapland.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter" }));
        await element.updateComplete;
        expect(lapland.getAttribute("aria-pressed")).toBe("true");
        expect(shadow(element).querySelector(".stats-title")?.textContent).toBe("Lapin hyvinvointialue");

        lapland.dispatchEvent(new KeyboardEvent("keydown", { key: " " }));
        await element.updateComplete;
        expect(lapland.getAttribute("aria-pressed")).toBe("false");
    });

    it("keeps the transform of the shapes that have one", async () => {
        const root = shadow(await card(hass()));
        expect(root.querySelector("#lapin_hyvinvointialue")?.getAttribute("transform")).toBeNull();
        expect(root.querySelector("#ahvenanmaa")?.getAttribute("transform")).toBe("translate(-528.85372,-914.75602)");
    });
});

describe("the size of the card", () => {
    it("lets the map scale with the card instead of fixing it in pixels", async () => {
        const root = shadow(await card(hass()));
        const svg = root.querySelector(".map svg") as SVGElement;
        expect(svg.getAttribute("width")).toBeNull();
        expect(svg.getAttribute("height")).toBeNull();
        expect(svg.getAttribute("viewBox")).toBe("0 0 1667.6923 2897.9419");
        expect((root.querySelector(".map") as HTMLElement).getAttribute("style")).toContain("aspect-ratio: 235 / 409");
    });

    it("places the numbers in proportion, so they scale with the map", async () => {
        const root = shadow(await card(hass()));
        const styles = [...root.querySelectorAll(".amount")].map((span) => span.getAttribute("style") ?? "");
        expect(styles.every((style) => style.includes("%"))).toBe(true);
        expect(styles.some((style) => style.includes("px"))).toBe(false);
        // Lapland's number is at its visual centre, well inside it.
        expect(styles.find((style) => style.startsWith("left: 6"))).toMatch(/^left: \d+\.\d{3}%; top: \d+\.\d{3}%;$/);
    });

    it("fixes the map at the width the configuration asks for", async () => {
        const root = shadow(await card(hass(), { entity: ENTITY, map_width: 320 }));
        const style = (root.querySelector(".map") as HTMLElement).getAttribute("style") ?? "";
        expect(style).toContain("width: 320px");
        expect(style).toContain("max-width: 100%");
    });

    it("offers a visual editor", async () => {
        const { ThlCard } = await import("../src/thl-card");
        const element = ThlCard.getConfigElement();
        expect(element.tagName.toLowerCase()).toBe("thl-card-editor");
    });
});

describe("the shape of the card", () => {
    it("is never squeezed below half a section", () => {
        const element = document.createElement("thl-card") as ThlCard;
        expect(element.getGridOptions()).toEqual({ columns: 12, rows: "auto", min_columns: 6 });
    });

    it("groups the figures, so they can sit in a row or a column", async () => {
        const root = shadow(await card(hass()));
        expect(root.querySelector(".figures")).not.toBeNull();
        expect(root.querySelectorAll(".figures .stats-container")).toHaveLength(1);
    });

    it("names the disease above the map, with the figures after it", async () => {
        const root = shadow(await card(hass()));
        const children = [...(root.querySelector(".card")?.children ?? [])].map((child) => child.className);
        expect(children).toEqual(["disease", "body", "key"]);
        const body = [...(root.querySelector(".body")?.children ?? [])].map((child) => child.className);
        expect(body).toEqual(["map", "side"]);
    });

    it("puts the figures beside the map by the card's own width, not by its columns", async () => {
        const { ThlCard } = await import("../src/thl-card");
        const styles = String((ThlCard as unknown as { styles: { cssText: string } }).styles.cssText);
        // A whole section in a view of four sections is about 307px, which must still put the figures beside the map.
        expect(styles).toContain("container: thl / inline-size");
        expect(styles).toContain("@container thl (min-width: 290px)");
        const narrow = shadow(await card(hass(), { entity: ENTITY, grid_options: { columns: 9 } }));
        const full = shadow(await card(hass(), { entity: ENTITY, grid_options: { columns: "full" } }));
        expect(narrow.querySelector(".card")?.className).toBe(full.querySelector(".card")?.className);
    });

    it("keeps the disease name with its drawing", async () => {
        const root = shadow(await card(hass()));
        const disease = root.querySelector(".disease");
        expect(disease?.querySelector(".disease-logo")).not.toBeNull();
        expect(disease?.querySelector(".disease-name")?.textContent?.trim()).toBe("Influenssa");
    });

    it("keeps the disease on one line and the map within bounds", async () => {
        const { ThlCard } = await import("../src/thl-card");
        const styles = String((ThlCard as unknown as { styles: { cssText: string } }).styles.cssText);
        expect(styles).toContain("white-space: nowrap");
        // The drawing and the gap are tied to the name's size, not scaled on their own.
        expect(styles).toContain("width: 1.7em");
        expect(styles).toContain("gap: 0.5em");
        // A number must never swallow the click meant for the county under it.
        expect(styles).toMatch(/\.amount \{[^}]*pointer-events: none/);
        expect(styles).toContain("width: min(100%, 300px)");
    });
});

describe("the drawings", () => {
    it("draws the virus in the theme's colours, so it shows on a dark card too", async () => {
        const root = shadow(await card(hass()));
        const drawing = root.querySelector(".disease-logo")?.outerHTML ?? "";
        expect(drawing).toContain("currentColor");
        expect(drawing).not.toMatch(/#000000|#FFFFFF/i);
    });
});

describe("the figures beside the map", () => {
    it("start with the whole country", async () => {
        const root = shadow(await card(hass()));
        const [whole] = root.querySelectorAll(".stats-container");
        expect(whole.querySelector(".stats-title")?.textContent).toContain("Koko maa");
        expect(whole.textContent).toContain("Viime viikko: 17");
        expect(whole.textContent).toContain("Toissa viikko: 20");
        expect(whole.textContent).toContain("Muutos: −15 % (−3)");
    });

    it("name the disease", async () => {
        const root = shadow(await card(hass()));
        expect(root.textContent).toContain("Influenssa");
    });

    it("show the chosen county instead of the whole country", async () => {
        const element = await card(hass());
        const root = shadow(element);
        expect(root.querySelectorAll(".stats-container")).toHaveLength(1);
        expect(root.querySelector(".stats-title")?.textContent).toContain("Koko maa");

        (root.querySelector("#kainuun_hyvinvointialue") as SVGElement).dispatchEvent(new Event("click"));
        await element.updateComplete;

        expect(root.querySelectorAll(".stats-container")).toHaveLength(1);
        expect(root.querySelector(".stats-title")?.textContent).toContain("Kainuun hyvinvointialue");
        expect(root.querySelector(".stats-container")?.textContent).toContain("Viime viikko: 0");
    });

    it("start with the default county when one is set", async () => {
        const element = await card(hass(), { entity: ENTITY, default_area: "kainuun_hyvinvointialue" });
        const root = shadow(element);
        expect(root.querySelector(".stats-title")?.textContent).toContain("Kainuun hyvinvointialue");
        expect(root.querySelector("#kainuun_hyvinvointialue")?.classList.contains("selected")).toBe(true);

        (root.querySelector("#kainuun_hyvinvointialue") as SVGElement).dispatchEvent(new Event("click"));
        await element.updateComplete;
        expect(root.querySelector(".stats-title")?.textContent).toContain("Koko maa");
    });

    it("go back to the whole country when the same county is clicked again", async () => {
        const element = await card(hass());
        const root = shadow(element);
        const county = root.querySelector("#kainuun_hyvinvointialue") as SVGElement;

        county.dispatchEvent(new Event("click"));
        await element.updateComplete;
        county.dispatchEvent(new Event("click"));
        await element.updateComplete;

        expect(root.querySelectorAll(".stats-container")).toHaveLength(1);
        expect(root.querySelector(".stats-title")?.textContent).toContain("Koko maa");
    });

    it("leave out the change when THL has not published the week before", async () => {
        const values: Area[] = [{ area_id: "finland", name: "Kaikki hyvinvointialueet", amount_last_week: 17 }];
        const root = shadow(await card(hass({ values })));
        const [whole] = root.querySelectorAll(".stats-container");
        expect(whole.textContent).toContain("Viime viikko: 17");
        expect(whole.textContent).not.toContain("Toissa viikko");
        expect(whole.textContent).not.toContain("undefined");
    });
});

describe("when there is nothing to show", () => {
    it("says so when the entity does not exist", async () => {
        const root = shadow(await card({ states: {}, locale: { language: "fi" } }));
        expect(root.textContent).toContain(ENTITY);
        expect(root.querySelector("svg")).toBeNull();
    });

    it("says so when the sensor is unavailable", async () => {
        const root = shadow(await card(hass({ state: "unavailable" })));
        expect(root.querySelector(".message")?.textContent?.trim()).toBe("Tautien lukumäärät eivät ole saatavilla.");
    });

    it("refuses a configuration without an entity", () => {
        const element = document.createElement("thl-card") as ThlCard;
        expect(() => element.setConfig({ type: "custom:thl-card" } as never)).toThrow();
    });
});

describe("by level and with a trend", () => {
    const LEVELS: Area[] = [
        {
            area_id: "finland",
            name: "Kaikki hyvinvointialueet",
            amount_last_week: 17,
            incidence_last_week: 0.3,
            entity_id: ENTITY,
            incidence_entity_id: "sensor.thl_influenssa_ilmaantuvuus",
        },
        {
            area_id: "lapin_hyvinvointialue",
            name: "Lapin hyvinvointialue",
            amount_last_week: 2,
            incidence_last_week: 1.1,
            entity_id: "sensor.thl_influenssa_lappi",
            incidence_entity_id: "sensor.thl_influenssa_lappi_ilmaantuvuus",
        },
        { area_id: "ahvenanmaa", name: "Ahvenanmaa", amount_last_week: 0, incidence_last_week: 0 },
    ];

    // Wednesday of week 38, 2026. The statistics have weeks 35 to 37 finished, with the figures of weeks 34 to 36, and a
    // row of the week still running, which the trend leaves out.
    beforeEach(() => {
        vi.useFakeTimers({ toFake: ["Date"] });
        vi.setSystemTime(new Date(2026, 8, 16, 12));
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    /** The trend's calls, without the year ago's, which ask for an end too. */
    const trendCalls = (callWS: ReturnType<typeof vi.fn>) => callWS.mock.calls.filter(([message]) => !message.end_time);

    function withTrend(values: Area[] = LEVELS) {
        const callWS = vi.fn().mockImplementation(async (message: { statistic_ids: string[] }) => ({
            [message.statistic_ids[0]]: [0, 1, 2, 9].map((mean, index) => ({ start: new Date(2026, 7, 25 + 7 * index).getTime(), mean })),
        }));
        return { state: { ...hass({ values }), callWS } as HomeAssistant, callWS };
    }

    async function settled(element: ThlCard): Promise<void> {
        await new Promise((resolve) => setTimeout(resolve, 0));
        await element.updateComplete;
    }

    it("colours a county by how it compares with the whole country", async () => {
        const root = shadow(await card(hass({ values: LEVELS })));
        const fill = (id: string) => root.querySelector(`#${id}`)?.getAttribute("style");
        expect(fill("lapin_hyvinvointialue")).toContain(RISING_FAST);
        expect(fill("ahvenanmaa")).toContain(NO_CASES);
    });

    it("shows the incidence with the cases", async () => {
        const root = shadow(await card(hass({ values: LEVELS })));
        expect(root.querySelector(".stats-container")?.textContent).toContain("Ilmaantuvuus: 0,3 / 100\u00a0000");
    });

    // Home Assistant's number format setting wins over the language, as its own frontend reads it, for every number the
    // card writes: the figures, the change and both legends. Hindi groups unlike every locale a setting maps to, and
    // unlike the test runners' own, so each row can fail on its own. Persian has digits of its own. The space before a
    // percent sign is the language's, as the frontend's blankBeforePercent has it: Finnish has one, Hindi and Persian don't.
    describe("the number format setting", () => {
        // The minus sign and the bidirectional marks are the locale's own business, not the setting's.
        const plain = (text: string) =>
            text
                .replace(/[\s\u00a0\u202f]+/g, " ")
                .replace(/\u2019/g, "'")
                .replace(/\u2212/g, "-")
                .replace(/[\u200e\u200f\u061c]/g, "")
                .trim();
        const system = (value: number, digits: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(value);
        const DOTS = { level: "0 < 0.5 < 0.8 ≈ 1 > 1.25 > 2", change_key: "0 -40% -10% ±10% +10% +40%" };
        const COMMAS = { level: "0 < 0,5 < 0,8 ≈ 1 > 1,25 > 2", change_key: DOTS.change_key };
        const SPACED = "0 -40 % -10 % ±10 % +10 % +40 %";
        it.each([
            {
                language: "hi",
                number_format: "language",
                incidence: "12,34,567.5 / 1,00,000",
                change: "-12,34,567%",
                cases: "12,34,567",
                ...DOTS,
            },
            {
                language: "hi",
                number_format: "comma_decimal",
                incidence: "1,234,567.5 / 100,000",
                change: "-1,234,567%",
                cases: "1,234,567",
                ...DOTS,
            },
            {
                language: "hi",
                number_format: "decimal_comma",
                incidence: "1.234.567,5 / 100.000",
                change: "-1.234.567%",
                cases: "1.234.567",
                ...COMMAS,
            },
            {
                language: "hi",
                number_format: "space_comma",
                incidence: "1 234 567,5 / 100 000",
                change: "-1 234 567%",
                cases: "1 234 567",
                ...COMMAS,
            },
            {
                language: "hi",
                number_format: "quote_decimal",
                incidence: "1'234'567.5 / 100'000",
                change: "-1'234'567%",
                cases: "1'234'567",
                ...DOTS,
            },
            { language: "hi", number_format: "none", incidence: "1234567.5 / 100000", change: "-1234567%", cases: "1234567", ...DOTS },
            // None is en-US without grouping, not the language without it, so a Finnish interface gets a decimal point.
            {
                language: "fi",
                number_format: "none",
                incidence: "1234567.5 / 100000",
                change: "-1234567 %",
                cases: "1234567",
                ...DOTS,
                change_key: SPACED,
            },
            {
                language: "fi",
                number_format: "language",
                incidence: "1 234 567,5 / 100 000",
                change: "-1 234 567 %",
                cases: "1 234 567",
                ...COMMAS,
                change_key: SPACED,
            },
            // Persian digits go when the setting names a locale, and Finnish unset is the UI language.
            {
                language: "fa",
                number_format: "comma_decimal",
                incidence: "1,234,567.5 / 100,000",
                change: "-1,234,567%",
                cases: "1,234,567",
                ...DOTS,
            },
            {
                language: "fi",
                number_format: undefined,
                incidence: "1 234 567,5 / 100 000",
                change: "-1 234 567 %",
                cases: "1 234 567",
                ...COMMAS,
                change_key: SPACED,
            },
            {
                language: "fa",
                number_format: "language",
                incidence: "۱٬۲۳۴٬۵۶۷٫۵ / ۱۰۰٬۰۰۰",
                change: "-۱٬۲۳۴٬۵۶۷%",
                cases: "۱٬۲۳۴٬۵۶۷",
                level: "۰ < ۰٫۵ < ۰٫۸ ≈ ۱ > ۱٫۲۵ > ۲",
                change_key: "۰ -۴۰% -۱۰% ±۱۰% +۱۰% +۴۰%",
            },
            {
                language: "hi",
                number_format: "system",
                incidence: `${system(1234567.5, 1)} / ${system(100000, 0)}`,
                change: `${system(-1234567, 0)}%`,
                cases: system(1234567, 0),
                level: [
                    system(0, 2),
                    `< ${system(0.5, 2)}`,
                    `< ${system(0.8, 2)}`,
                    `≈ ${system(1, 0)}`,
                    `> ${system(1.25, 2)}`,
                    `> ${system(2, 0)}`,
                ].join(" "),
                change_key: `${system(0, 0)} -${system(40, 0)}% -${system(10, 0)}% ±${system(10, 0)}% +${system(10, 0)}% +${system(40, 0)}%`,
            },
        ])(
            "writes every number in the format $number_format in the language $language",
            async ({ language, number_format, incidence, change, cases, level, change_key }) => {
                const values = [
                    {
                        ...LEVELS[0],
                        amount_last_week: 1234567,
                        incidence_last_week: 1234567.5,
                        change_percentage: "-1234567",
                        change_in_numbers: -1234567,
                    },
                    { ...LEVELS[1], amount_last_week: 1234567 },
                ];
                const state = { ...hass({ values }), locale: { language, number_format } };
                const bounds = (root: ShadowRoot) =>
                    plain([...root.querySelectorAll(".key .bounds span")].map((span) => span.textContent).join(" "));
                const byLevel = shadow(await card(state));
                const figures = plain(byLevel.querySelector(".stats-container")?.textContent ?? "");
                // Last week's cases are the only figure followed by a space: the incidence goes on with its decimals.
                expect(figures).toContain(`: ${plain(cases)} `);
                expect(figures).toContain(plain(incidence));
                expect(figures).toContain(`: ${plain(change)} (-${plain(cases)})`);
                expect([...byLevel.querySelectorAll(".amount")].map((label) => plain(label.textContent ?? ""))).toContain(plain(cases));
                expect(bounds(byLevel)).toBe(plain(level));
                document.body.innerHTML = "";
                const byChange = shadow(await card(state, { entity: ENTITY, color_by: "change" }));
                expect(bounds(byChange)).toBe(plain(change_key));
            },
        );

        // The trend's week numbers and its count of weeks are numbers too.
        it.each([
            { language: "fi", number_format: undefined, caption: "4 viikkoa", bubble: "Vk 35: 1" },
            { language: "fa", number_format: "language", caption: "۴ weeks", bubble: "Wk ۳۵: ۱" },
            { language: "fa", number_format: "comma_decimal", caption: "4 weeks", bubble: "Wk 35: 1" },
        ])(
            "writes the trend's weeks in the format $number_format in the language $language",
            async ({ language, number_format, caption, bubble }) => {
                const { state } = withTrend();
                const element = await card({ ...state, locale: { language, number_format } });
                await settled(element);
                const root = shadow(element);
                expect(plain(root.querySelector(".trend-caption")?.textContent ?? "")).toContain(caption);
                const plot = root.querySelector(".trend-plot") as HTMLElement;
                plot.getBoundingClientRect = () => ({ left: 0, width: 100, top: 0, height: 40 }) as DOMRect;
                plot.dispatchEvent(new PointerEvent("pointermove", { clientX: 49 }));
                await element.updateComplete;
                expect(plain(root.querySelector(".trend-bubble")?.textContent ?? "")).toBe(bubble);
            },
        );

        // The system row's text can't fail on a runner whose own locale is the one a mistake would pick, so the locale is
        // checked too: the system setting leaves it to the browser.
        it("leaves the locale to the browser with the system setting", async () => {
            const formats = vi.spyOn(Intl, "NumberFormat");
            await card({ ...hass({ values: LEVELS }), locale: { language: "hi", number_format: "system" } });
            expect(formats).toHaveBeenCalled();
            expect(formats.mock.calls.map(([locales]) => locales)).toEqual(formats.mock.calls.map(() => undefined));
            formats.mockRestore();
        });
    });

    it("follows a change of language without waiting for the sensor", async () => {
        const state = hass({ values: LEVELS });
        const element = await card(state);
        element.hass = { ...state, locale: { language: "en" } };
        await element.updateComplete;
        expect(shadow(element).querySelector(".stats-container")?.textContent).toContain("Incidence: 0.3 / 100,000");
    });

    it("draws the trend of the whole country’s incidence, then of the chosen county", async () => {
        const { state, callWS } = withTrend();
        const element = await card(state);
        await settled(element);
        const root = shadow(element);

        expect(callWS.mock.calls[0][0].statistic_ids).toEqual(["sensor.thl_influenssa_ilmaantuvuus"]);
        expect(root.querySelector(".trend polyline.trend-line")).not.toBeNull();
        // Three finished weeks, and the figure of week 37 the sensor shows now.
        expect(root.querySelector(".trend-caption")?.textContent).toContain("4 viikkoa");

        (root.querySelector("#lapin_hyvinvointialue") as SVGElement).dispatchEvent(new Event("click"));
        await settled(element);
        expect(trendCalls(callWS).at(-1)?.[0].statistic_ids).toEqual(["sensor.thl_influenssa_lappi_ilmaantuvuus"]);
    });

    it("covers six months, and names the week and figure the pointer is at", async () => {
        const { state, callWS } = withTrend();
        const element = await card(state);
        await settled(element);
        const root = shadow(element);
        const start = new Date(callWS.mock.calls[0][0].start_time).getTime();
        expect(Math.round((Date.now() - start) / (7 * 24 * 60 * 60 * 1000))).toBeGreaterThanOrEqual(26);

        const plot = root.querySelector(".trend-plot") as HTMLElement;
        plot.getBoundingClientRect = () => ({ left: 0, width: 100, top: 0, height: 40 }) as DOMRect;
        plot.dispatchEvent(new PointerEvent("pointermove", { clientX: 49 }));
        await element.updateComplete;
        expect(root.querySelector(".trend-bubble")?.textContent?.replace(/\s+/g, " ").trim()).toBe("Vk 35: 1");

        plot.dispatchEvent(new PointerEvent("pointerleave"));
        await element.updateComplete;
        expect(root.querySelector(".trend-bubble")).toBeNull();
    });

    it("names the newest point by the week the sensor shows", async () => {
        const { state } = withTrend();
        const element = await card(state);
        await settled(element);
        const plot = shadow(element).querySelector(".trend-plot") as HTMLElement;
        plot.getBoundingClientRect = () => ({ left: 0, width: 100, top: 0, height: 40 }) as DOMRect;
        plot.dispatchEvent(new PointerEvent("pointermove", { clientX: 100 }));
        await element.updateComplete;
        expect(shadow(element).querySelector(".trend-bubble")?.textContent).toContain("Vk 37: 0,3");
    });

    it("shows a tapped week until the next touch, and steps along the trend with the arrow keys", async () => {
        const { state } = withTrend();
        const element = await card(state);
        await settled(element);
        const root = shadow(element);
        const plot = root.querySelector(".trend-plot") as HTMLElement;
        plot.getBoundingClientRect = () => ({ left: 0, width: 100, top: 0, height: 40 }) as DOMRect;
        const bubble = () => root.querySelector(".trend-bubble")?.textContent?.replace(/\s+/g, " ").trim();

        plot.dispatchEvent(new PointerEvent("pointerdown", { clientX: 0, pointerType: "touch" }));
        plot.dispatchEvent(new PointerEvent("pointerleave", { pointerType: "touch" }));
        await element.updateComplete;
        expect(bubble()).toBe("Vk 34: 0");

        plot.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight" }));
        await element.updateComplete;
        expect(bubble()).toBe("Vk 35: 1");
        plot.dispatchEvent(new KeyboardEvent("keydown", { key: "End" }));
        await element.updateComplete;
        expect(bubble()).toBe("Vk 37: 0,3");
    });

    it("tries again later when the statistics couldn't be fetched", async () => {
        const { state, callWS } = withTrend();
        callWS.mockRejectedValueOnce(new Error("Connection lost"));
        vi.useFakeTimers({ toFake: ["Date", "setTimeout", "clearTimeout"] });
        vi.setSystemTime(new Date(2026, 8, 16, 12));
        const element = await card(state);
        await vi.advanceTimersByTimeAsync(0);
        expect(shadow(element).querySelector(".trend")).toBeNull();

        await vi.advanceTimersByTimeAsync(60 * 1000);
        await element.updateComplete;
        expect(trendCalls(callWS)).toHaveLength(2);
        expect(shadow(element).querySelector(".trend")).not.toBeNull();
    });

    it("draws the cases when colouring by change", async () => {
        const { state, callWS } = withTrend();
        await settled(await card(state, { entity: ENTITY, color_by: "change" }));
        expect(callWS.mock.calls[0][0].statistic_ids).toEqual([ENTITY]);
    });

    it("draws the newest figure again when THL corrects it during the week", async () => {
        const { state, callWS } = withTrend();
        const element = await card(state);
        await settled(element);
        const corrected = LEVELS.map((area) => (area.area_id === "finland" ? { ...area, incidence_last_week: 0.4 } : area));
        element.hass = {
            ...state,
            states: { [ENTITY]: { ...state.states[ENTITY]!, attributes: { ...state.states[ENTITY]!.attributes, values: corrected } } },
        };
        await settled(element);
        expect(trendCalls(callWS)).toHaveLength(2);
        expect(shadow(element).querySelector(".trend-caption")?.textContent).toContain("4 viikkoa");
    });

    it("doesn't break when the point pointed at is gone from a shorter trend", async () => {
        const { state } = withTrend();
        const element = await card(state);
        await settled(element);
        (element as unknown as { hovered: number }).hovered = 25;
        await element.updateComplete;
        expect(shadow(element).querySelector(".trend-bubble")?.textContent).toContain("Vk 37");
    });

    it("tries a failed fetch again when the card is shown again, if it was hidden before the retry", async () => {
        const { state, callWS } = withTrend();
        callWS.mockRejectedValueOnce(new Error("Connection lost"));
        const element = await card(state);
        await settled(element);
        expect(shadow(element).querySelector(".trend")).toBeNull();
        element.remove();
        document.body.append(element);
        await settled(element);
        expect(trendCalls(callWS)).toHaveLength(2);
        expect(shadow(element).querySelector(".trend")).not.toBeNull();
    });

    it("draws no trend when asked not to", async () => {
        const { state, callWS } = withTrend();
        const element = await card(state, { entity: ENTITY, show_trend: false });
        await settled(element);
        expect(trendCalls(callWS)).toHaveLength(0);
        expect(shadow(element).querySelector(".trend")).toBeNull();
    });

    it("does not ask again when nothing it depends on changed", async () => {
        const { state, callWS } = withTrend();
        const element = await card(state);
        await settled(element);
        element.hass = { ...state, states: { ...state.states } };
        await settled(element);
        expect(callWS).toHaveBeenCalledTimes(2);
        expect(trendCalls(callWS)).toHaveLength(1);
    });
});

describe("the flu-like illness visits", () => {
    const VISITS: Area[] = [
        {
            area_id: "finland",
            name: "Kaikki alueet",
            share_last_week: 0.0125,
            share_two_weeks_ago: 0.011,
            visits_last_week: 250,
            all_visits_last_week: 2000000,
            entity_id: "sensor.thl_influenssankaltaiset_kaynnit",
        },
        {
            area_id: "lapin_hyvinvointialue",
            name: "Lapin hyvinvointialue",
            share_last_week: 0.05,
            visits_last_week: 12,
            all_visits_last_week: 24000,
        },
    ];

    function visits(): HomeAssistant {
        return {
            locale: { language: "fi" },
            states: {
                "sensor.thl_influenssankaltaiset_kaynnit": {
                    entity_id: "sensor.thl_influenssankaltaiset_kaynnit",
                    state: "0.0125",
                    attributes: { friendly_name: "THL Influenssankaltaiset käynnit", last_week: 37, values: VISITS },
                },
            },
        };
    }

    // The space before a percent sign is the language's, as the frontend's blankBeforePercent has it: only cs, de, fi, fr,
    // sk and sv have one, by their exact code, so Swiss German has none.
    describe("the percent sign of a share", () => {
        it.each([
            { language: "fi", last: "Viime viikko: 0,5 %", before: "Toissa viikko: 0,25 %" },
            { language: "sv", last: "Last week: 0,5 %", before: "Two weeks ago: 0,25 %" },
            { language: "de", last: "Last week: 0,5 %", before: "Two weeks ago: 0,25 %" },
            { language: "cs", last: "Last week: 0,5 %", before: "Two weeks ago: 0,25 %" },
            { language: "fr", last: "Last week: 0,5 %", before: "Two weeks ago: 0,25 %" },
            { language: "sk", last: "Last week: 0,5 %", before: "Two weeks ago: 0,25 %" },
            // A language with its region isn't one of the codes, so Finnish in Finland has none, as in the frontend.
            { language: "fi-FI", last: "Viime viikko: 0,5%", before: "Toissa viikko: 0,25%" },
            { language: "en", last: "Last week: 0.5%", before: "Two weeks ago: 0.25%" },
            { language: "hi", last: "Last week: 0.5%", before: "Two weeks ago: 0.25%" },
            { language: "de-CH", last: "Last week: 0.5%", before: "Two weeks ago: 0.25%" },
        ])("is written $last in the language $language", async ({ language, last, before }) => {
            const state = { ...visits(), locale: { language } };
            const sensor = state.states["sensor.thl_influenssankaltaiset_kaynnit"]!;
            sensor.attributes = {
                ...sensor.attributes,
                values: [{ ...VISITS[0], share_last_week: 0.5, share_two_weeks_ago: 0.25 }, VISITS[1]],
            };
            const root = shadow(await card(state, { entity: "sensor.thl_influenssankaltaiset_kaynnit" }));
            const figures = (root.querySelector(".stats-container")?.textContent ?? "").replace(/[\s\u00a0]+/g, " ");
            expect(figures).toContain(last);
            expect(figures).toContain(before);
        });
    });

    it("are named after their sensor", async () => {
        const root = shadow(await card(visits(), { entity: "sensor.thl_influenssankaltaiset_kaynnit" }));
        expect(root.querySelector(".disease-name")?.textContent?.trim()).toBe("Influenssankaltaiset käynnit");
    });

    it("show the share of visits and how many there were", async () => {
        const root = shadow(await card(visits(), { entity: "sensor.thl_influenssankaltaiset_kaynnit" }));
        const figures = root.querySelector(".stats-container")?.textContent?.replace(/\s+/g, " ");
        expect(figures).toContain("Viime viikko: 0,013 %");
        expect(figures).toContain("Käynnit: 250 / 2 000 000");
        expect(figures).toContain("Toissa viikko: 0,011 %");
    });

    it("colour by the change of the share when asked to", async () => {
        const values = [VISITS[0], { ...VISITS[1], share_two_weeks_ago: 0.1 }];
        const state = visits();
        state.states["sensor.thl_influenssankaltaiset_kaynnit"]!.attributes.values = values;
        const root = shadow(await card(state, { entity: "sensor.thl_influenssankaltaiset_kaynnit", color_by: "change" }));
        expect(root.querySelector("#lapin_hyvinvointialue")?.getAttribute("style")).toContain(FALLING_FAST);
    });

    it("write the visits on the map and colour by the share", async () => {
        const root = shadow(await card(visits(), { entity: "sensor.thl_influenssankaltaiset_kaynnit" }));
        const labels = [...root.querySelectorAll(".amount")].map((span) => span.textContent?.trim());
        expect(labels).toContain("12");
        expect(root.querySelector("#lapin_hyvinvointialue")?.getAttribute("style")).toContain(RISING_FAST);
    });
});

describe("the capital region", () => {
    it("is drawn again larger beside the figures, with its numbers there instead of on the map", async () => {
        const root = shadow(await card(hass()));
        const inset = root.querySelector(".side .inset");
        expect(inset).not.toBeNull();
        expect(inset?.getAttribute("aria-hidden")).toBe("true");
        expect(inset?.querySelector(".inset-caption")?.textContent).toBe("Pääkaupunkiseutu");
        expect(inset?.querySelectorAll(".amount")).toHaveLength(3);
        expect(root.querySelectorAll(".map .amount")).toHaveLength(20);
        expect(root.querySelector(".map .frame")).not.toBeNull();
    });

    it("chooses a county clicked in the inset", async () => {
        const element = await card(hass());
        const paths = [...shadow(element).querySelectorAll(".inset path")];
        expect(paths.length).toBeGreaterThan(3);
        // The inset's copies are for the pointer only: the keyboard reaches the counties on the map.
        expect(paths.every((path) => !path.hasAttribute("tabindex") && !path.hasAttribute("id"))).toBe(true);
        paths[0].dispatchEvent(new Event("click"));
        await element.updateComplete;
        expect(shadow(element).querySelector(".inset .selected-outline")).not.toBeNull();
        expect(shadow(element).querySelector(".map .selected-outline")).not.toBeNull();
    });

    it("stays on the map when the inset is turned off, Helsinki's number moved into the sea off Vantaa's", async () => {
        const values = [...AREAS, { area_id: "helsingin_kaupunki", name: "Helsingin kaupunki", amount_last_week: 186 }];
        const root = shadow(await card(hass({ values }), { entity: ENTITY, show_inset: false }));
        expect(root.querySelector(".inset")).toBeNull();
        expect(root.querySelector(".frame")).toBeNull();
        const labels = [...root.querySelectorAll(".map .amount")];
        expect(labels).toHaveLength(23);
        const helsinki = labels.find((label) => label.textContent === "186")?.getAttribute("style") ?? "";
        expect(Number(/top: ([\d.]+)%/.exec(helsinki)?.[1])).toBeGreaterThan(97);
    });

    it("writes the numbers on the map in the user's number format", async () => {
        const values = [...AREAS, { area_id: "kanta-hameen_hyvinvointialue", name: "Kanta-Häme", amount_last_week: 1234 }];
        const root = shadow(await card(hass({ values })));
        expect([...root.querySelectorAll(".amount")].some((label) => /^1\s234$/.test(label.textContent ?? ""))).toBe(true);
    });
});

describe("the chosen county", () => {
    it("keeps its colour and gets an outline drawn over its neighbours, the counties keeping their order", async () => {
        const element = await card(hass(), { entity: ENTITY, default_area: "pirkanmaan_hyvinvointialue" });
        const root = shadow(element);
        const order = [...root.querySelectorAll(".map path[id]")].map((path) => path.id);
        const outline = root.querySelector(".map .selected-outline");
        expect(outline?.getAttribute("d")).toBe(root.querySelector("#pirkanmaan_hyvinvointialue")?.getAttribute("d"));
        expect(outline?.parentElement?.lastElementChild).toBe(outline);

        (root.querySelector("#lapin_hyvinvointialue") as SVGElement).dispatchEvent(new Event("click"));
        await element.updateComplete;
        expect([...root.querySelectorAll(".map path[id]")].map((path) => path.id)).toEqual(order);
    });
});

describe("the colour key", () => {
    it("says what the colours mean, by level against the whole country", async () => {
        const key = shadow(await card(hass())).querySelector(".key");
        expect(key?.querySelectorAll(".swatches span")).toHaveLength(6);
        expect([...(key?.querySelectorAll(".bounds span") ?? [])].map((span) => span.textContent)).toEqual([
            "0",
            "< 0,5",
            "< 0,8",
            "≈ 1",
            "> 1,25",
            "> 2",
        ]);
        expect(key?.querySelector(".key-caption")?.textContent).toBe("ilmaantuvuus koko maahan verrattuna");
    });

    it("gives the bounds of the change when colouring by change", async () => {
        const key = shadow(await card(hass(), { entity: ENTITY, color_by: "change" })).querySelector(".key");
        expect(key?.querySelector(".bounds span:last-child")?.textContent).toBe("+40 %");
        expect(key?.querySelector(".key-caption")?.textContent).toBe("muutos edellisestä viikosta");
    });

    it("is left out when asked", async () => {
        expect(shadow(await card(hass(), { entity: ENTITY, show_key: false })).querySelector(".key")).toBeNull();
    });
});

describe("several diseases", () => {
    function two(): HomeAssistant {
        const state = hass();
        state.states["sensor.thl_norovirus"] = {
            entity_id: "sensor.thl_norovirus",
            state: "40",
            attributes: { disease_name: "Norovirus", last_week: 37, values: [{ ...AREAS[0], amount_last_week: 40 }, AREAS[1]] },
        };
        return state;
    }

    it("are switched between with a button each, the chosen county staying chosen", async () => {
        const element = await card(two(), { entity: [ENTITY, "sensor.thl_norovirus"], default_area: "lapin_hyvinvointialue" });
        const root = shadow(element);
        const chips = [...root.querySelectorAll(".chip")] as HTMLButtonElement[];
        expect(chips.map((chip) => chip.textContent?.trim())).toEqual(["Influenssa", "Norovirus"]);
        expect(chips[0].getAttribute("aria-pressed")).toBe("true");

        chips[1].click();
        await element.updateComplete;
        expect(root.querySelector(".disease-name")?.textContent?.trim()).toBe("Norovirus");
        expect(root.querySelector(".stats-title")?.textContent).toBe("Lapin hyvinvointialue");
    });

    it("has no buttons for one", async () => {
        expect(shadow(await card(two())).querySelector(".chips")).toBeNull();
        expect(shadow(await card(two(), { entity: [ENTITY] })).querySelector(".chips")).toBeNull();
    });
});

describe("the same week a year ago", () => {
    it("is shown when the statistics reach that far, and left out when they don't", async () => {
        const shortCalls = vi.fn().mockResolvedValue({});
        const callWS = vi.fn().mockImplementation(async (message: { end_time?: string; statistic_ids: string[] }) => {
            if (!message.end_time) {
                return {};
            }
            // Week 37's figure was shown during week 38 a year ago, from Monday 15 September 2025.
            return { [message.statistic_ids[0]]: [{ start: new Date(2025, 8, 16).getTime(), mean: 24 }] };
        });
        vi.useFakeTimers({ toFake: ["Date"] });
        vi.setSystemTime(new Date(2026, 8, 16, 12));
        const values = AREAS.map((area) => ({ ...area, entity_id: `sensor.${area.area_id}` }));
        const element = await card({ ...hass({ values }), callWS } as HomeAssistant);
        await new Promise((resolve) => setTimeout(resolve, 0));
        await element.updateComplete;
        vi.useRealTimers();
        expect(shadow(element).querySelector(".stats-container")?.textContent?.replace(/\s+/g, " ")).toContain("Vuosi sitten: 24");

        const without = await card({ ...hass({ values }), callWS: shortCalls } as HomeAssistant);
        await new Promise((resolve) => setTimeout(resolve, 0));
        await without.updateComplete;
        expect(shortCalls.mock.calls.some(([message]) => message.end_time)).toBe(true);
        expect(shadow(without).querySelector(".stats-container")?.textContent).not.toContain("Vuosi sitten");
    });
});
