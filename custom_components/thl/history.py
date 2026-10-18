"""Writing past weeks into the statistics of a sensor, so its graphs have a past from the start.

Each week's figure is stored at the start of the week after it, which is when the
sensor would have shown it: THL publishes a week's numbers during the following
week. The recorder's own statistics of the running sensor carry on the same way,
so the imported past and the recorded present line up.

Only the weeks with no statistics at all are written, so a sensor that has been running keeps what it recorded
itself, and gets the weeks before it, such as when the past kept grew from six months to a year.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from homeassistant.components.recorder import DATA_INSTANCE, get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, statistics_during_period
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .statistics import Week

_LOGGER = logging.getLogger(__name__)

# Statistics imported by an integration for one of its own entities say they come from the recorder.
SOURCE = "recorder"
# The recorder compiles an hour's statistics a little after it ends. A row imported into an hour it hasn't compiled
# yet makes that compile hit a duplicate and roll back the hour for every entity, so the newest hours are left to it.
COMPILE_MARGIN = timedelta(hours=2)


def shown_from(week: Week) -> datetime:
    """The start of the week after, in Home Assistant's time zone."""
    monday = week.monday + timedelta(weeks=1)
    return dt_util.as_utc(datetime.combine(monday, time(), tzinfo=dt_util.get_default_time_zone()))


def recording(hass: HomeAssistant) -> bool:
    """Whether there is a recorder to keep statistics in."""
    return DATA_INSTANCE in hass.data


async def weeks_with_statistics(hass: HomeAssistant, statistic_id: str, since: datetime) -> set[float]:
    """The starts of the weeks since then that have any statistics, recorded or imported.

    The recorder's weeks start on Monday at midnight in Home Assistant's time zone, as a week shown from does.
    """
    found = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, since, None, {statistic_id}, "week", None, {"mean"}
    )
    return {row["start"] for row in found.get(statistic_id, [])}


async def async_import_history(hass: HomeAssistant, entity_id: str, unit: str | None, points: list[tuple[Week, float | None]]) -> bool:
    """Writes the weeks that have no statistics into the sensor's statistics. Tells whether it wrote any."""
    if not points or not recording(hass):
        return False

    now = dt_util.utcnow()
    known = [(start, value) for week, value in points if value is not None and (start := shown_from(week)) <= now - COMPILE_MARGIN]
    if not known:
        return False
    taken = await weeks_with_statistics(hass, entity_id, min(start for start, _ in known))
    rows = [StatisticData(start=start, mean=value, min=value, max=value) for start, value in known if start.timestamp() not in taken]
    if not rows:
        return False

    metadata = StatisticMetaData(
        source=SOURCE,
        statistic_id=entity_id,
        name=None,
        unit_of_measurement=unit,
        unit_class=None,
        mean_type=StatisticMeanType.ARITHMETIC,
        has_sum=False,
    )
    async_import_statistics(hass, metadata, rows)
    _LOGGER.debug("Wrote %s weeks into the statistics of %s", len(rows), entity_id)
    return True
