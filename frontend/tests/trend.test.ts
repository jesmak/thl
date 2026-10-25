import { afterEach, describe, expect, it, vi } from "vitest";

import type { HomeAssistant } from "../src/hass";
import { fetchTrend, fetchYearAgo, isoWeek, weekStart, weeklyPoints, weeksAfter, weeksBefore, withCurrent } from "../src/trend";

// Week 38 of 2026 starts on Monday 14 September; the tests run in Helsinki's time.
const MONDAY = new Date(2026, 8, 14).getTime();
const NOW = new Date(2026, 8, 16, 12).getTime();
const DAY = 24 * 60 * 60 * 1000;

/** A day's row as Home Assistant gives it, starting at midnight of a day some weeks before week 38's Monday. */
const day = (weeks: number, days = 0) => new Date(2026, 8, 14 - 7 * weeks + days).getTime();

afterEach(() => {
    process.env.TZ = "Europe/Helsinki";
});

describe("the trend", () => {
    it("starts a week on its Monday", () => {
        expect(weekStart(MONDAY + 3 * DAY + 5000)).toBe(MONDAY);
        expect(weekStart(MONDAY)).toBe(MONDAY);
        expect(weekStart(MONDAY - 1)).toBe(day(1));
    });

    it("numbers weeks as ISO does", () => {
        expect(isoWeek(MONDAY)).toBe(38);
        expect(isoWeek(new Date(2026, 0, 1).getTime())).toBe(1);
        expect(isoWeek(new Date(2027, 0, 1).getTime())).toBe(53);
    });

    it("takes the last value of each finished week, labelled with the week before, whose figure it is", () => {
        const rows = [
            { start: day(2), mean: 4 },
            { start: day(1), mean: 4 },
            { start: day(1, 2), mean: 5 },
            { start: day(1, 3), mean: null },
        ];
        expect(weeklyPoints(rows, 12, NOW)).toEqual([
            { week: 35, value: 4 },
            { week: 36, value: 5 },
        ]);
    });

    it("leaves out the week still running, whose figure may not be in the statistics yet", () => {
        const rows = [
            { start: day(1), mean: 4 },
            { start: day(0, 1), mean: 6 },
        ];
        expect(weeklyPoints(rows, 12, NOW)).toEqual([{ week: 36, value: 4 }]);
    });

    it("keeps only the newest weeks asked for", () => {
        const rows = [4, 3, 2, 1].map((weeks) => ({ start: day(weeks), mean: weeks }));
        expect(weeklyPoints(rows, 2, NOW).map((point) => point.value)).toEqual([2, 1]);
    });

    it("labels the weeks right across the spring clock change", () => {
        // Clocks go forward on Sunday 29 March 2026, between week 13 and week 14.
        const rows = [16, 23, 30, 6].map((date, index) => ({ start: new Date(2026, index < 3 ? 2 : 3, date).getTime(), mean: index }));
        const points = weeklyPoints(rows, 12, new Date(2026, 3, 15).getTime());
        expect(points.map((point) => point.week)).toEqual([11, 12, 13, 14]);
    });

    it("puts Home Assistant's days in the right week for a viewer in another time zone", () => {
        // Midnight on Monday in Helsinki is still Sunday in UTC.
        const rows = [{ start: "2026-09-06T21:00:00+00:00", mean: 3 }];
        process.env.TZ = "UTC";
        expect(weeklyPoints(rows, 12, Date.parse("2026-09-16T12:00:00Z"))).toEqual([{ week: 36, value: 3 }]);
    });

    it("steps back whole weeks by the calendar", () => {
        // From after the clock change to before it, still Monday at midnight.
        expect(new Date(weeksBefore(new Date(2026, 3, 6).getTime(), 2)).getHours()).toBe(0);
    });

    it("adds the figure the sensor shows when it is newer than the last finished week's", () => {
        const points = [
            { week: 35, value: 4 },
            { week: 36, value: 5 },
        ];
        expect(withCurrent(points, 37, 7, 26)).toEqual([...points, { week: 37, value: 7 }]);
        expect(withCurrent(points, 36, 5, 26)).toEqual(points);
        expect(withCurrent(points, 37, 7, 2)).toEqual([points[1], { week: 37, value: 7 }]);
        expect(withCurrent(points, undefined, 7, 26)).toEqual(points);
    });

    it("counts weeks across the turn of a year", () => {
        expect(weeksAfter(2, 51)).toBe(4);
        expect(weeksAfter(51, 2)).toBe(-4);
        expect(weeksAfter(37, 37)).toBe(0);
    });

    it("leaves out a week THL published nothing in, which repeats the week before under the wrong name", () => {
        // On the Monday of week 44 the sensor still shows week 41: week 43 kept week 41's figure and is named 42.
        const points = [
            { week: 40, value: 120 },
            { week: 41, value: 130 },
            { week: 42, value: 130 },
        ];
        expect(withCurrent(points, 41, 130, 26)).toEqual(points.slice(0, 2));
        // Once THL catches up with week 43, week 42's real figure takes the place of the repeat.
        expect(withCurrent(points.slice(0, 2), 43, 150, 26)).toEqual([...points.slice(0, 2), { week: 43, value: 150 }]);
    });

    it("asks Home Assistant for the daily statistics of the sensor, from six months of whole weeks back", async () => {
        const callWS = vi.fn().mockResolvedValue({ "sensor.x": [{ start: new Date(day(1)).toISOString(), mean: 1 }] });
        const hass = { states: {}, callWS } as unknown as HomeAssistant;

        expect(await fetchTrend(hass, "sensor.x", 4, NOW)).toEqual([{ week: 36, value: 1 }]);
        expect(callWS).toHaveBeenCalledWith({
            type: "recorder/statistics_during_period",
            start_time: new Date(day(4)).toISOString(),
            statistic_ids: ["sensor.x"],
            period: "day",
            types: ["mean"],
        });
    });

    it("finds a week's figure a year ago in the finished week after it, and nothing when the statistics stop short", async () => {
        // Week 37 of 2025 was shown during week 38, from Monday 15 September 2025.
        const callWS = vi.fn().mockResolvedValue({
            "sensor.x": [
                { start: new Date(2025, 8, 9).getTime(), mean: 20 },
                { start: new Date(2025, 8, 16).getTime(), mean: 24 },
                { start: new Date(2025, 8, 23).getTime(), mean: 30 },
            ],
        });
        const hass = { states: {}, callWS } as unknown as HomeAssistant;
        expect(await fetchYearAgo(hass, "sensor.x", 37, NOW)).toBe(24);
        expect(callWS.mock.calls[0][0]).toMatchObject({
            start_time: new Date(day(55)).toISOString(),
            end_time: new Date(day(50)).toISOString(),
        });

        callWS.mockResolvedValue({});
        expect(await fetchYearAgo(hass, "sensor.x", 37, NOW)).toBeUndefined();
    });

    it("is empty without Home Assistant’s websocket", async () => {
        expect(await fetchTrend({ states: {} }, "sensor.x", 4)).toEqual([]);
    });
});
