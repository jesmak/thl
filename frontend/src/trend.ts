/**
 * The trend of an area, from the statistics the thl integration keeps for the area's sensor.
 *
 * A week's figure is published during the week after it, so a sensor changes in
 * the middle of a week. Averaging a week would mix two figures; the last value of
 * each week is the newest figure that week had, and it is the figure of the week before.
 */
import type { HomeAssistant } from "./hass";

export interface TrendPoint {
    /** The ISO week the figure is from. */
    week: number;
    value: number;
}

interface StatisticRow {
    start: number | string;
    mean?: number | null;
}

/**
 * Home Assistant starts a day's statistics at midnight in its own time zone. Counting from the middle of that day
 * puts it on the same date for a viewer up to twelve hours ahead or behind.
 */
const HALF_DAY = 12 * 60 * 60 * 1000;

/** The Monday of the week a moment falls in, at midnight in the viewer's time. */
export function weekStart(moment: number): number {
    const date = new Date(moment);
    date.setHours(0, 0, 0, 0);
    date.setDate(date.getDate() - ((date.getDay() + 6) % 7));
    return date.getTime();
}

/** The same moment some weeks earlier, by the calendar, so a clock change in between doesn't move it off its day. */
export function weeksBefore(moment: number, weeks: number): number {
    const date = new Date(moment);
    date.setDate(date.getDate() - 7 * weeks);
    return date.getTime();
}

/** The ISO week number of a moment, in the viewer's time. */
export function isoWeek(moment: number): number {
    const date = new Date(moment);
    date.setHours(0, 0, 0, 0);
    // The Thursday of the week decides its year, and so its number.
    date.setDate(date.getDate() + 3 - ((date.getDay() + 6) % 7));
    const firstThursday = new Date(date.getFullYear(), 0, 4);
    firstThursday.setDate(firstThursday.getDate() + 3 - ((firstThursday.getDay() + 6) % 7));
    return 1 + Math.round((date.getTime() - firstThursday.getTime()) / (7 * 24 * 60 * 60 * 1000));
}

/**
 * The last value of each finished week, oldest first, for the given number of newest weeks, each labelled with the
 * week its figure is from. The week still running is left out: its figure may not be in the statistics yet.
 */
export function weeklyPoints(rows: StatisticRow[], weeks: number, now: number = Date.now()): TrendPoint[] {
    const running = weekStart(now);
    const byWeek = new Map<number, number>();
    for (const row of rows) {
        if (row.mean === null || row.mean === undefined) {
            continue;
        }
        const start = typeof row.start === "number" ? row.start : Date.parse(row.start);
        const week = weekStart(start + HALF_DAY);
        // The rows come oldest first, so a later row of the same week replaces an earlier one.
        if (week < running) {
            byWeek.set(week, row.mean);
        }
    }
    return [...byWeek.entries()]
        .sort(([a], [b]) => a - b)
        .slice(-weeks)
        .map(([week, value]) => ({ week: isoWeek(weeksBefore(week, 1)), value }));
}

/** How many weeks `week` is after `other`, across the turn of a year: negative when it is before. */
export function weeksAfter(week: number, other: number): number {
    const ahead = (((week - other) % 53) + 53) % 53;
    return ahead > 26 ? ahead - 53 : ahead;
}

/**
 * The trend with the figure the sensor shows now added at the end, when it is newer than the last finished week's.
 * A figure published this week is not in last week's statistics.
 *
 * A finished week is named by the week before it, which is wrong when THL published nothing that week: it kept the
 * figure of a week earlier. Such points, named after the week the sensor shows, are left out, as they repeat it.
 */
export function withCurrent(points: TrendPoint[], week: number | undefined, value: number | undefined, weeks: number): TrendPoint[] {
    if (week === undefined) {
        return points;
    }
    const known = points.filter((point) => weeksAfter(point.week, week) <= 0);
    if (value === undefined || known.at(-1)?.week === week) {
        return known;
    }
    return [...known, { week, value }].slice(-weeks);
}

/**
 * The figure of a week a year ago: the week a year back whose finished statistics carry that week's figure. Nothing
 * when Home Assistant's statistics don't reach that far, as for a sensor that hasn't been given a year of its past.
 */
export async function fetchYearAgo(
    hass: HomeAssistant,
    statisticId: string,
    week: number,
    now: number = Date.now(),
): Promise<number | undefined> {
    if (!hass.callWS) {
        return undefined;
    }
    // A year is 52 or 53 weeks, and the figure is shown the week after its own, so a few weeks around it are asked for.
    const end = weeksBefore(weekStart(now), 50);
    const result = await hass.callWS<Record<string, StatisticRow[]>>({
        type: "recorder/statistics_during_period",
        start_time: new Date(weeksBefore(weekStart(now), 55)).toISOString(),
        end_time: new Date(end).toISOString(),
        statistic_ids: [statisticId],
        period: "day",
        types: ["mean"],
    });
    return weeklyPoints(result[statisticId] ?? [], 5, end).find((point) => point.week === week)?.value;
}

/** Fetches the finished weeks of one sensor's trend. Nothing when Home Assistant has no statistics for it. */
export async function fetchTrend(hass: HomeAssistant, statisticId: string, weeks: number, now: number = Date.now()): Promise<TrendPoint[]> {
    if (!hass.callWS) {
        return [];
    }
    const start = new Date(weeksBefore(weekStart(now), weeks)).toISOString();
    const result = await hass.callWS<Record<string, StatisticRow[]>>({
        type: "recorder/statistics_during_period",
        start_time: start,
        statistic_ids: [statisticId],
        period: "day",
        types: ["mean"],
    });
    return weeklyPoints(result[statisticId] ?? [], weeks, now);
}
