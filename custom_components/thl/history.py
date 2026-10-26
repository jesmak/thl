"""Keeping each week's figure in the statistics of a sensor as THL has it now, so its graphs have a past from the start.

Each week's figure is stored in the week after it, which is when the sensor shows
it: THL publishes a week's numbers during the following week. A week with no
statistics gets one row at its start. In a week that has some, every row is given
the figure, as the recorder keeps whatever the sensor showed in each hour: the
figure of the week before until THL published, and a figure THL later corrected.
The hours missing from a week stay missing.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime, time, timedelta

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import (
    STATISTIC_UNIT_TO_UNIT_CONVERTER,
    async_import_statistics,
    statistics_during_period,
)
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .statistics import Week

_LOGGER = logging.getLogger(__name__)

# Statistics imported by an integration for one of its own entities say they come from the recorder.
SOURCE = "recorder"
# The recorder compiles an hour's statistics a little after it ends. A row imported into an hour it hasn't compiled
# yet makes that compile hit a duplicate and roll back the hour for every entity, so no row is added to the newest
# hours. A row the recorder has already compiled can be given the figure.
COMPILE_MARGIN = timedelta(hours=2)
# The hour being recorded when THL's figures change is compiled later from both the old figure and the new one, so the
# weeks are written once more after it has been.
WRITE_AGAIN_AFTER = timedelta(hours=1) + COMPILE_MARGIN
WEEK = timedelta(weeks=1)


def midnight(day: date) -> datetime:
    return dt_util.as_utc(datetime.combine(day, time(), tzinfo=dt_util.get_default_time_zone()))


def shown_from(week: Week) -> datetime:
    """The start of the week after, in Home Assistant's time zone."""
    return midnight(week.monday + WEEK)


def shown_until(week: Week) -> datetime:
    """The end of the week after. A week with a clock change in it is an hour longer or shorter than seven days."""
    return midnight(week.monday + 2 * WEEK)


def recording(hass: HomeAssistant) -> bool:
    """Whether there is a recorder to keep statistics in. One whose database failed is not set up."""
    return "recorder" in hass.config.components


def unit_class(unit: str | None) -> str | None:
    """The unit class the recorder gives a sensor without a device class, so an import doesn't change it back and forth."""
    converter = STATISTIC_UNIT_TO_UNIT_CONVERTER.get(unit)
    return converter.UNIT_CLASS if converter else None


def same(stored: float | None, figure: float) -> bool:
    # A mean of equal values may come back a rounding error away from them.
    return stored is not None and math.isclose(stored, figure, rel_tol=1e-9, abs_tol=1e-12)


async def async_write_history(hass: HomeAssistant, sensors: list[tuple[str, str | None, list[tuple[Week, float | None]]]]) -> None:
    """Gives each week in the statistics of each sensor THL's figure for it: its entity id, unit and weekly figures.

    One subentry's sensors are asked about in one query, and the hours of the weeks to correct in another.
    """
    if not recording(hass):
        return

    now = dt_util.utcnow()
    known: dict[str, tuple[str | None, list[tuple[datetime, datetime, float]]]] = {}
    for entity_id, unit, points in sensors:
        found = [(shown_from(week), shown_until(week), value) for week, value in points if value is not None]
        if found := [slot for slot in found if slot[0] <= now]:
            known[entity_id] = (unit, found)
    if not known:
        return
    instance = get_instance(hass)
    # The recorder's weeks start on Monday at midnight in Home Assistant's time zone, as a week shown from does.
    since = min(start for _, found in known.values() for start, _, _ in found)
    weeks = await instance.async_add_executor_job(statistics_during_period, hass, since, None, set(known), "week", None, {"min", "max"})

    rows: dict[str, list[StatisticData]] = {}
    # The weeks whose rows hold something else than the figure, by sensor: their start, end and figure.
    wrong: dict[str, list[tuple[datetime, datetime, float]]] = {}
    for entity_id, (_, found) in known.items():
        taken = {row["start"]: row for row in weeks.get(entity_id, [])}
        for start, end, value in found:
            row = taken.get(start.timestamp())
            if row is None:
                if start <= now - COMPILE_MARGIN:
                    rows.setdefault(entity_id, []).append(StatisticData(start=start, mean=value, min=value, max=value))
            elif not (same(row.get("min"), value) and same(row.get("max"), value)):
                wrong.setdefault(entity_id, []).append((start, end, value))

    if wrong:
        since = min(start for slots in wrong.values() for start, _, _ in slots)
        recorded = await instance.async_add_executor_job(statistics_during_period, hass, since, None, set(wrong), "hour", None, {"mean"})
        for entity_id, slots in wrong.items():
            for row in recorded.get(entity_id, []):
                hour = dt_util.utc_from_timestamp(row["start"])
                for start, end, value in slots:
                    if start <= hour < end:
                        rows.setdefault(entity_id, []).append(StatisticData(start=hour, mean=value, min=value, max=value))

    for entity_id, written in rows.items():
        metadata = StatisticMetaData(
            source=SOURCE,
            statistic_id=entity_id,
            name=None,
            unit_of_measurement=known[entity_id][0],
            unit_class=unit_class(known[entity_id][0]),
            mean_type=StatisticMeanType.ARITHMETIC,
            has_sum=False,
        )
        async_import_statistics(hass, metadata, written)
        _LOGGER.debug("Wrote %s hours into the statistics of %s", len(written), entity_id)
