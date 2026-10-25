import { beforeEach, describe, expect, it } from "vitest";

import { cardEntities } from "../src/editor";
import type { ThlCardEditor } from "../src/editor";
import type { HomeAssistant } from "../src/hass";
import type { ThlCardConfig } from "../src/types";

const THL = "Data provided by Finnish Institute for Health and Welfare (THL)";

const hass: HomeAssistant = {
    locale: { language: "fi" },
    states: {
        "sensor.thl_influenssa": {
            entity_id: "sensor.thl_influenssa",
            state: "17",
            attributes: {
                values: [
                    { area_id: "finland", name: "Kaikki hyvinvointialueet" },
                    { area_id: "lapin_hyvinvointialue", name: "Lapin hyvinvointialue" },
                    { area_id: "etela-karjalan_hyvinvointialue", name: "Etelä-Karjalan hyvinvointialue" },
                ],
                attribution: THL,
            },
        },
        "sensor.thl_influenssankaltaiset_kaynnit": {
            entity_id: "sensor.thl_influenssankaltaiset_kaynnit",
            state: "0.01",
            attributes: { values: [], attribution: THL },
        },
        // A county's sensor has no areas to draw.
        "sensor.thl_influenssa_lappi": {
            entity_id: "sensor.thl_influenssa_lappi",
            state: "2",
            attributes: { attribution: THL },
        },
    },
};

async function editor(config: Partial<ThlCardConfig> = {}): Promise<ThlCardEditor> {
    const element = document.createElement("thl-card-editor") as ThlCardEditor;
    element.setConfig({ type: "custom:thl-card", entity: "sensor.thl_influenssa", ...config } as ThlCardConfig);
    element.hass = hass;
    document.body.append(element);
    await element.updateComplete;
    return element;
}

function form(element: ThlCardEditor): HTMLElement & { schema: Array<Record<string, unknown>>; data: unknown } {
    const found = element.shadowRoot?.querySelector("ha-form");
    if (!found) {
        throw new Error("the editor rendered no form");
    }
    return found as HTMLElement & { schema: Array<Record<string, unknown>>; data: unknown };
}

beforeEach(() => {
    document.body.innerHTML = "";
});

describe("the visual editor", () => {
    it("asks for one or several whole country sensors of the thl integration", async () => {
        const [entity] = form(await editor()).schema;
        expect(entity.name).toBe("entity");
        expect(entity.required).toBe(true);
        expect(entity.selector).toEqual({
            entity: {
                multiple: true,
                domain: "sensor",
                integration: "thl",
                include_entities: ["sensor.thl_influenssa", "sensor.thl_influenssankaltaiset_kaynnit"],
            },
        });
    });

    it("leaves the county sensors out of the choice", () => {
        expect(cardEntities(hass)).not.toContain("sensor.thl_influenssa_lappi");
    });

    it("offers the colours, the trend, the inset, the key and a width for the map", async () => {
        const names = form(await editor()).schema.map((entry) => entry.name);
        expect(names).toEqual(["entity", "color_by", "default_area", "show_trend", "show_inset", "show_key", "map_width"]);
    });

    it("offers the counties of the chosen sensor as the default, after the whole country", async () => {
        const entry = form(await editor()).schema.find((field) => field.name === "default_area");
        const options = (entry?.selector as { select: { options: Array<{ value: string; label: string }> } }).select.options;
        expect(options.map((option) => option.value)).toEqual(["", "etela-karjalan_hyvinvointialue", "lapin_hyvinvointialue"]);
        expect(options[0].label).toBe("Koko maa");
    });

    it("drops a default county set back to the whole country", async () => {
        const element = await editor({ default_area: "lapin_hyvinvointialue" });
        const changes: ThlCardConfig[] = [];
        element.addEventListener("config-changed", (event) => {
            changes.push((event as CustomEvent<{ config: ThlCardConfig }>).detail.config);
        });
        form(element).dispatchEvent(
            new CustomEvent("value-changed", {
                detail: { value: { type: "custom:thl-card", entity: "sensor.thl_influenssa", default_area: "" } },
            }),
        );
        expect(changes[0]).not.toHaveProperty("default_area");
    });

    it("shows the defaults it leaves out of the configuration", async () => {
        expect(form(await editor()).data).toMatchObject({ color_by: "level", show_trend: true, show_inset: true, show_key: true });
    });

    it("keeps the defaults out of what it passes on", async () => {
        const element = await editor();
        const changes: ThlCardConfig[] = [];
        element.addEventListener("config-changed", (event) => {
            changes.push((event as CustomEvent<{ config: ThlCardConfig }>).detail.config);
        });

        form(element).dispatchEvent(
            new CustomEvent("value-changed", {
                detail: {
                    value: {
                        type: "custom:thl-card",
                        entity: "sensor.thl_influenssa",
                        color_by: "change",
                        show_trend: true,
                    },
                },
            }),
        );

        expect(changes[0]).toEqual({
            type: "custom:thl-card",
            entity: "sensor.thl_influenssa",
            color_by: "change",
        });
    });

    it("shows the configuration it was given", async () => {
        expect(form(await editor({ map_width: 300 })).data).toMatchObject({
            entity: ["sensor.thl_influenssa"],
            map_width: 300,
        });
    });

    it("keeps one sensor a plain entity, and several a list", async () => {
        const changed = async (config: Partial<ThlCardConfig>, entity: string[]) => {
            const element = await editor(config);
            const changes: ThlCardConfig[] = [];
            element.addEventListener("config-changed", (event) =>
                changes.push((event as CustomEvent<{ config: ThlCardConfig }>).detail.config),
            );
            form(element).dispatchEvent(new CustomEvent("value-changed", { detail: { value: { type: "custom:thl-card", entity } } }));
            return changes[0].entity;
        };
        expect(await changed({}, ["sensor.thl_influenssa"])).toBe("sensor.thl_influenssa");
        expect(await changed({}, ["sensor.thl_influenssa", "sensor.thl_norovirus"])).toEqual([
            "sensor.thl_influenssa",
            "sensor.thl_norovirus",
        ]);
        // A list the user wrote stays a list, even of one.
        expect(await changed({ entity: ["sensor.thl_influenssa", "sensor.thl_norovirus"] }, ["sensor.thl_influenssa"])).toEqual([
            "sensor.thl_influenssa",
        ]);
    });

    it("offers the counties of the first sensor when there are several", async () => {
        const element = await editor({ entity: ["sensor.thl_influenssa", "sensor.thl_influenssankaltaiset_kaynnit"] });
        const entry = form(element).schema.find((field) => field.name === "default_area");
        expect((entry?.selector as { select: { options: unknown[] } }).select.options).toHaveLength(3);
    });

    it("names the fields in the viewer’s language", async () => {
        const element = await editor();
        const compute = (form(element) as unknown as { computeLabel(entry: { name: string }): string }).computeLabel;
        expect(compute({ name: "entity" })).toBe("Taudit tai influenssankaltaiset käynnit");
        expect(compute({ name: "color_by" })).toBe("Värit");
        expect(compute({ name: "map_width" })).toBe("Kartan leveys");
    });

    it("passes on what the user changed", async () => {
        const element = await editor();
        const changes: ThlCardConfig[] = [];
        element.addEventListener("config-changed", (event) => {
            changes.push((event as CustomEvent<{ config: ThlCardConfig }>).detail.config);
        });

        form(element).dispatchEvent(
            new CustomEvent("value-changed", {
                detail: { value: { type: "custom:thl-card", entity: "sensor.thl_norovirus", map_width: 320 } },
            }),
        );

        expect(changes).toHaveLength(1);
        expect(changes[0]).toEqual({ type: "custom:thl-card", entity: "sensor.thl_norovirus", map_width: 320 });
    });

    it("drops an emptied width, so the map follows the card again", async () => {
        const element = await editor({ map_width: 320 });
        const changes: ThlCardConfig[] = [];
        element.addEventListener("config-changed", (event) => {
            changes.push((event as CustomEvent<{ config: ThlCardConfig }>).detail.config);
        });

        form(element).dispatchEvent(
            new CustomEvent("value-changed", {
                detail: { value: { type: "custom:thl-card", entity: "sensor.thl_influenssa", map_width: "" } },
            }),
        );

        expect(changes[0]).not.toHaveProperty("map_width");
    });
});
