import { describe, expect, it } from "vitest";

import {
    caseCount,
    changeColor,
    changePercentage,
    changeText,
    fillColor,
    FALLING,
    FALLING_FAST,
    findArea,
    isVisits,
    level,
    levelColor,
    NO_CASES,
    NO_DATA,
    RISING,
    RISING_FAST,
    STEADY,
} from "../src/areas";
import type { Area } from "../src/types";

function area(values: Partial<Area> = {}): Area {
    return {
        area_id: "lapin_hyvinvointialue",
        name: "Lapin hyvinvointialue",
        amount_last_week: 2,
        amount_two_weeks_ago: 1,
        change_in_numbers: 1,
        change_percentage: "100",
        ...values,
    };
}

describe("finding a county", () => {
    it("is found by the id the integration uses", () => {
        const areas = [area(), area({ area_id: "finland", name: "Kaikki hyvinvointialueet" })];
        expect(findArea(areas, "finland")?.name).toBe("Kaikki hyvinvointialueet");
        expect(findArea(areas, "ahvenanmaa")).toBeUndefined();
    });

    it("writes nothing on the map for a county the sensor does not carry", () => {
        expect(caseCount([area({ amount_last_week: 7 })], "lapin_hyvinvointialue")).toBe(7);
        expect(caseCount([], "lapin_hyvinvointialue")).toBe("");
    });

    it("reads the change whether it comes as a string or a number", () => {
        expect(changePercentage(area({ change_percentage: "-43" }))).toBe(-43);
        expect(changePercentage(area({ change_percentage: 0 }))).toBe(0);
        expect(changePercentage(area({ change_percentage: undefined }))).toBeNaN();
    });
});

describe("colouring by change", () => {
    it("is the text colour when the sensor has no numbers for it", () => {
        expect(changeColor(undefined)).toBe(NO_DATA);
    });

    it("is blue when there were no cases at all, this week or before", () => {
        expect(changeColor(area({ amount_last_week: 0, change_percentage: 0 }))).toBe(NO_CASES);
    });

    it("is not blue when the change is a real reading of no change", () => {
        expect(changeColor(area({ amount_last_week: 0, change_percentage: "0" }))).toBe(STEADY);
    });

    it.each([
        ["-100", FALLING_FAST],
        ["-43", FALLING_FAST],
        ["-41", FALLING_FAST],
        ["-40", FALLING],
        ["-15", FALLING],
        ["-10", STEADY],
        ["0", STEADY],
        ["10", STEADY],
        ["15", RISING],
        ["40", RISING],
        ["41", RISING_FAST],
        ["100", RISING_FAST],
    ])("is right for a change of %s per cent", (change, expected) => {
        expect(changeColor(area({ change_percentage: change }))).toBe(expected);
    });

    it("is the steady colour when THL has not published the week before", () => {
        expect(changeColor(area({ change_percentage: undefined, amount_two_weeks_ago: undefined }))).toBe(STEADY);
    });

    it("takes the change of the share for the flu-like illness visits, which come without one", () => {
        expect(changePercentage(area({ change_percentage: undefined, share_last_week: 0.03, share_two_weeks_ago: 0.02 }))).toBeCloseTo(50);
        expect(changeColor(area({ change_percentage: undefined, share_last_week: 0.03, share_two_weeks_ago: 0.02 }))).toBe(RISING_FAST);
        expect(changeColor(area({ change_percentage: undefined, share_last_week: 0.019, share_two_weeks_ago: 0.02 }))).toBe(STEADY);
        expect(changeColor(area({ change_percentage: undefined, share_last_week: 0, share_two_weeks_ago: 0 }))).toBe(NO_CASES);
        expect(changeColor(area({ change_percentage: undefined, share_last_week: 0.02, share_two_weeks_ago: null }))).toBe(STEADY);
        // No visits at all, so no share to change.
        expect(changeColor(area({ change_percentage: undefined, share_last_week: null, share_two_weeks_ago: 0.02 }))).toBe(NO_DATA);
    });

    // The number 0 means there was nothing the week before, the string "0" a real reading of no change.
    describe("the change as written", () => {
        const finnish = (value: number) => `${new Intl.NumberFormat("fi").format(value)} %`;
        it.each([
            { change_percentage: 0, text: "–" },
            { change_percentage: "0", text: "0 %" },
            { change_percentage: "-15", text: "−15 %" },
            { change_percentage: "1400", text: "1\u00a0400 %" },
            { change_percentage: "not a number", text: "–" },
        ])("is $text for $change_percentage", ({ change_percentage, text }) => {
            expect(changeText(area({ change_percentage }), finnish)).toBe(text);
        });
    });
});

describe("the colour of a county", () => {
    it("is by level unless asked otherwise", () => {
        const whole = area({ area_id: "finland", incidence_last_week: 1 });
        expect(fillColor(area({ incidence_last_week: 3, change_percentage: "-50" }), undefined, whole)).toBe(RISING_FAST);
        expect(fillColor(area({ incidence_last_week: 3, change_percentage: "-50" }), "change", whole)).toBe(FALLING_FAST);
    });
});

describe("colouring by level", () => {
    const whole = area({ area_id: "finland", incidence_last_week: 2 });

    it.each([
        [0.5, FALLING_FAST],
        [1.2, FALLING],
        [2, STEADY],
        [2.5, STEADY],
        [3, RISING],
        [5, RISING_FAST],
    ])("a county at %s per 100 000 against the whole country’s 2", (incidence, expected) => {
        expect(fillColor(area({ incidence_last_week: incidence }), "level", whole)).toBe(expected);
    });

    it("leaves a county without cases the colour of no cases", () => {
        expect(levelColor(area({ incidence_last_week: 0 }), whole)).toBe(NO_CASES);
        expect(levelColor(area({ incidence_last_week: 0 }), area({ incidence_last_week: 0 }))).toBe(NO_CASES);
    });

    it("falls back to the change for a sensor without incidence", () => {
        expect(levelColor(area({ change_percentage: "-100" }), area({ area_id: "finland" }))).toBe(FALLING_FAST);
    });

    it("compares the share of flu-like illness visits the same way", () => {
        const country = area({ area_id: "finland", share_last_week: 0.01 });
        expect(levelColor(area({ share_last_week: 0.03 }), country)).toBe(RISING_FAST);
        expect(levelColor(area({ share_last_week: null }), country)).toBe(NO_DATA);
    });

    it("knows the flu-like illness visits from a disease", () => {
        expect(isVisits([area({ area_id: "finland", share_last_week: 0.01 })])).toBe(true);
        expect(isVisits([area({ area_id: "finland", incidence_last_week: 0.3 })])).toBe(false);
        expect(level(area({ share_last_week: 0.01 }))).toBe(0.01);
        expect(caseCount([area({ amount_last_week: undefined, visits_last_week: 12 })], "lapin_hyvinvointialue")).toBe(12);
    });
});
