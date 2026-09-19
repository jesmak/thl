"""Writing past weeks into the statistics of a new sensor, so its graphs have a past from the start.

Each week's figure is stored at the start of the week after it, which is when the
sensor would have shown it: THL publishes a week's numbers during the following
week. The recorder's own statistics of the running sensor carry on the same way,
so the imported past and the recorded present line up.

Only a sensor with no statistics at all gets a past. One that has been running
already has its own, and those are left alone.
"""

from __future__ import annotations

import logging
from datetime import datetime, time, timedelta

from homeassistant.components.recorder import DATA_INSTANCE, get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, get_last_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .statistics import Week

_LOGGER = logging.getLogger(__name__)

# Statistics imported by an integration for one of its own entities say they come from the recorder.
SOURCE = "recorder"


def shown_from(week: Week) -> datetime:
    """The start of the week after, in Home Assistant's time zone."""
    monday = week.monday + timedelta(weeks=1)
    return dt_util.as_utc(datetime.combine(monday, time(), tzinfo=dt_util.get_default_time_zone()))


def recording(hass: HomeAssistant) -> bool:
    """Whether there is a recorder to keep statistics in."""
    return DATA_INSTANCE in hass.data


async def has_statistics(hass: HomeAssistant, statistic_id: str) -> bool:
    found = await get_instance(hass).async_add_executor_job(get_last_statistics, hass, 1, statistic_id, True, {"mean"})
    return bool(found.get(statistic_id))


async def async_import_history(
    hass: HomeAssistant, entity_id: str, unit: str | None, points: list[tuple[Week, float | None]]
) -> bool:
    """Writes the weeks into the sensor's statistics, unless it already has some. Tells whether it wrote any."""
    if not points or not recording(hass) or await has_statistics(hass, entity_id):
        return False

    now = dt_util.utcnow()
    rows = [
        StatisticData(start=start, mean=value, min=value, max=value)
        for week, value in points
        if value is not None and (start := shown_from(week)) <= now
    ]
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
