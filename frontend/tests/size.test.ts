import { afterEach, describe, expect, it } from "vitest";

import "../src/thl-card";
import type { ThlCard } from "../src/thl-card";
import type { HomeAssistant } from "../src/hass";
import { browserLanguage, translate } from "../src/localize/localize";

const ENTITY = "sensor.thl_influenssa";
const OTHER = "sensor.thl_norovirus";

function hass(): HomeAssistant {
    const sensor = (entity_id: string, disease_name: string) => ({
        entity_id,
        state: "17",
        attributes: {
            disease_name,
            last_week: 37,
            values: [
                {
                    area_id: "finland",
                    name: "Kaikki hyvinvointialueet",
                    amount_last_week: 17,
                    amount_two_weeks_ago: 20,
                    change_in_numbers: -3,
                    change_percentage: "-15",
                    incidence_last_week: 0.3,
                },
            ],
        },
    });
    return { locale: { language: "fi" }, states: { [ENTITY]: sensor(ENTITY, "Influenssa"), [OTHER]: sensor(OTHER, "Norovirus") } };
}

async function card(config: Record<string, unknown> = {}, layout?: string): Promise<ThlCard> {
    const element = document.createElement("thl-card") as ThlCard;
    element.setConfig({ type: "custom:thl-card", entity: ENTITY, show_trend: false, ...config } as never);
    element.hass = hass();
    element.layout = layout;
    document.body.append(element);
    await element.updateComplete;
    return element;
}

function one(element: Element, selector: string): HTMLElement {
    return element.shadowRoot!.querySelector<HTMLElement>(selector)!;
}

// happy-dom lays nothing out, so each part is given the box it would have, measured from the card's top.
function box(target: Element, top: number, bottom: number): void {
    target.getBoundingClientRect = () => ({ top, bottom, height: bottom - top, width: 300 }) as DOMRect;
}

function style(element: ThlCard): string {
    return one(element, "ha-card").getAttribute("style") ?? "";
}

/** Lays the card out with its last part ending at `end`, fills its rows and returns its style. */
async function filled(element: ThlCard, end: number): Promise<string> {
    const haCard = one(element, "ha-card");
    Object.defineProperty(haCard, "clientWidth", { value: 300, configurable: true });
    box(haCard, 0, 56);
    box(one(element, ".content").lastElementChild!, end - 32, end);
    (element as unknown as { fillRows(): void }).fillRows();
    await element.updateComplete;
    return style(element);
}

afterEach(() => {
    document.body.innerHTML = "";
});

describe("filling the rows of a sections view", () => {
    // The content ends 12 px of padding under its last part: at 150 px with it ending at 138.
    it.each([
        ["whole rows", {}, "min-height: 184px; --spare: 34px"],
        ["half rows", { row_step: "half" }, "min-height: 152px; --spare: 2px"],
    ])("on automatic rows, ends on %s", async (_name, config, expected) => {
        expect(await filled(await card(config, "grid"), 138)).toBe(expected);
    });

    it("puts the spare room under the disease, and doesn't count it again once drawn", async () => {
        const element = await card({}, "grid");
        expect(await filled(element, 138)).toBe("min-height: 184px; --spare: 34px");
        one(element, ".disease").style.setProperty("padding-bottom", "34px");
        expect(await filled(element, 172)).toBe("min-height: 184px; --spare: 34px");
    });

    it("measures to its last part's end, never an element a theme adds after it", async () => {
        const element = await card({}, "grid");
        const added = document.createElement("div");
        box(added, 0, 900);
        one(element, "ha-card").append(added);
        expect(await filled(element, 138)).toBe("min-height: 184px; --spare: 34px");
    });

    it.each([
        ["outside a sections view", {}, undefined, ""],
        ["held by its rows", { grid_options: { rows: 9 } }, "grid", "height: 100%"],
        ["held to a fixed height", { height: 600 }, "grid", "height: 600px"],
    ])("leaves its height alone %s", async (_name, config, layout, expected) => {
        expect(await filled(await card(config, layout), 138)).toBe(expected);
    });

    // 700 px rounded down to the rows is 696, over the card's least height.
    it.each([
        ["under it, on the rows its content needs", 138, "max-height: 696px; min-height: 184px; --spare: 34px"],
        ["over it, on the limit rounded down to the rows", 900, "max-height: 696px; min-height: 696px; --spare: 0px"],
    ])("grows up to a limit on automatic rows %s", async (_name, end, expected) => {
        expect(await filled(await card({ max_height: 700 }, "grid"), end)).toBe(expected);
    });

    it("refuses a step that isn't whole or half rows", () => {
        const element = document.createElement("thl-card") as ThlCard;
        const config = (row_step: unknown) => ({ type: "custom:thl-card", entity: ENTITY, row_step }) as never;
        const error = translate(browserLanguage(), "invalid_row_step");
        expect(error).toMatch(/^Invalid rounding\./);
        for (const row_step of [undefined, null, "full", "half"]) {
            expect(() => element.setConfig(config(row_step))).not.toThrow();
        }
        expect(() => element.setConfig(config("quarter"))).toThrow(error);
    });
});

describe("a card held to a height", () => {
    it("gives every text that may be cut short its whole text as a tooltip", async () => {
        const element = await card({ grid_options: { rows: 9 }, show_trend: true }, "grid");
        expect(one(element, ".disease-name").title).toBe("Influenssa");
        expect(one(element, ".stats-title").title).toBe("Koko maa");
        const lines = [...element.shadowRoot!.querySelectorAll<HTMLElement>(".stats")];
        expect(lines.length).toBeGreaterThan(1);
        for (const line of lines) {
            expect(line.title.replace(/\s+/g, " ")).toBe(line.textContent?.replace(/\s+/g, " ").trim());
        }
        expect(one(element, ".key-caption").title).toBe(one(element, ".key-caption").textContent?.trim());
    });

    it("keeps its texts to one line, and the sensors' buttons on one line that scrolls sideways", async () => {
        const { ThlCard } = await import("../src/thl-card");
        const styles = String((ThlCard as unknown as { styles: { cssText: string } }).styles.cssText);
        expect(styles).toMatch(/ha-card\.held :is\(\.key-caption, \.trend-caption\) \{[^}]*white-space: nowrap/);
        // The figures only under the map, as over its sea they add no height.
        expect(styles).toMatch(/not \(min-width: 290px\) \{\s*ha-card\.held :is\(\.stats-title, \.stats\) \{[^}]*white-space: nowrap/);
        expect(styles).toMatch(/\.chips \{[^}]*overflow-x: auto/);
        expect(styles).not.toMatch(/\.chips \{[^}]*flex-wrap: wrap/);
    });

    it("keeps the figures over the map's sea where they would be without the buttons", async () => {
        const { ThlCard } = await import("../src/thl-card");
        const styles = String((ThlCard as unknown as { styles: { cssText: string } }).styles.cssText);
        expect(styles).toMatch(/\.chip \{[^}]*height: 25px/);
        expect(styles).toContain("--chips-room: 37px");
        expect(styles).toMatch(/\.card:has\(> \.chips\) \.side \{\s*top: calc\(16% - var\(--chips-room\)\)/);
        expect(styles).toMatch(
            /ha-card\.held \.card:has\(> \.chips\) \.side \{\s*top: calc\(0\.16 \* \(100% \+ var\(--chips-room\)\) - var\(--chips-room\)\)/,
        );
    });

    it.each([
        ["all of it in view", 200, 200, 0, []],
        ["more to the right at the start", 400, 200, 0, ["fade-right"]],
        ["more on both sides in the middle", 400, 200, 100, ["fade-left", "fade-right"]],
        ["more to the left at the end", 400, 200, 200, ["fade-left"]],
        ["a pixel over, which rounding gives", 201, 200, 0, []],
    ])("fades the line of buttons where it runs on, with %s", async (_name, scrollWidth, clientWidth, scrollLeft, fades) => {
        const { markChipFades } = await import("../src/thl-card");
        const line = document.createElement("div");
        Object.defineProperty(line, "scrollWidth", { value: scrollWidth });
        Object.defineProperty(line, "clientWidth", { value: clientWidth });
        line.scrollLeft = scrollLeft;
        Object.defineProperty(line, "scrollLeft", { value: scrollLeft });
        markChipFades(line);
        expect([...line.classList].filter((name) => name.startsWith("fade-"))).toEqual(fades);
        expect(line.classList.contains("draggable")).toBe(scrollWidth - clientWidth > 1);
    });

    describe("dragged with a mouse", () => {
        async function overflowing(): Promise<{ element: ThlCard; line: HTMLElement; chips: HTMLElement[] }> {
            const element = await card({ entity: [ENTITY, OTHER] });
            const line = one(element, ".chips");
            Object.defineProperty(line, "scrollWidth", { value: 400, configurable: true });
            Object.defineProperty(line, "clientWidth", { value: 200, configurable: true });
            return { element, line, chips: [...line.querySelectorAll<HTMLElement>(".chip")] };
        }

        function pointer(target: HTMLElement, type: string, clientX: number, pointerType = "mouse"): void {
            target.dispatchEvent(new PointerEvent(type, { bubbles: true, composed: true, clientX, pointerId: 1, pointerType, button: 0 }));
        }

        it("scrolls the line, and the click that ends the drag doesn't choose a button", async () => {
            const { element, line, chips } = await overflowing();
            pointer(chips[1], "pointerdown", 150);
            pointer(chips[1], "pointermove", 100);
            expect(line.scrollLeft).toBe(50);
            pointer(chips[1], "pointerup", 100);
            chips[1].click();
            await element.updateComplete;
            expect(chips[1].getAttribute("aria-pressed")).toBe("false");
            // The next click is an ordinary one.
            chips[1].click();
            await element.updateComplete;
            expect(chips[1].getAttribute("aria-pressed")).toBe("true");
        });

        it("still clicks after a few pixels of wobble", async () => {
            const { element, line, chips } = await overflowing();
            pointer(chips[1], "pointerdown", 150);
            pointer(chips[1], "pointermove", 147);
            pointer(chips[1], "pointerup", 147);
            chips[1].click();
            await element.updateComplete;
            expect(line.scrollLeft).toBe(0);
            expect(chips[1].getAttribute("aria-pressed")).toBe("true");
        });

        it("leaves a finger to the browser's own scrolling", async () => {
            const { line, chips } = await overflowing();
            pointer(chips[1], "pointerdown", 150, "touch");
            pointer(chips[1], "pointermove", 100, "touch");
            expect(line.scrollLeft).toBe(0);
        });
    });

    it("scrolls the chosen sensor's button into view along its line", async () => {
        // The line is drawn from 100 to 300 px, so its fades are 24 px and a button is clear of them from 124 to 276.
        const element = await card({ entity: [ENTITY, OTHER] });
        const line = one(element, ".chips");
        const chips = [...line.querySelectorAll<HTMLElement>(".chip")];
        Object.defineProperty(line, "clientWidth", { value: 200, configurable: true });
        line.getBoundingClientRect = () => ({ left: 100, right: 300 }) as DOMRect;
        const scrolled: number[] = [];
        line.scrollBy = ((options: ScrollToOptions) => scrolled.push(options.left ?? 0)) as typeof line.scrollBy;
        const click = async (index: number, left: number, right: number) => {
            chips[index].getBoundingClientRect = () => ({ left, right }) as DOMRect;
            scrolled.length = 0;
            chips[index].click();
            await element.updateComplete;
            await Promise.resolve();
            return [...scrolled];
        };
        // Past the right edge: until its end is 24 px in from it.
        expect(await click(1, 250, 330)).toEqual([54]);
        // Under the left fade: until its start is 24 px in.
        expect(await click(0, 110, 180)).toEqual([-14]);
        // Clear of both fades already: left where it is.
        expect(await click(1, 150, 230)).toEqual([]);
        // The button already shown, clicked again while under a fade, is brought into view too.
        expect(await click(1, 260, 290)).toEqual([14]);
    });
});
