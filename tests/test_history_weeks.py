"""Each week's statistics hold THL's current figure for it, whatever the sensor showed at the time."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, get_metadata, statistics_during_period
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.components.recorder.common import async_wait_recording_done

from custom_components.thl.history import async_write_history, shown_from
from custom_components.thl.statistics import Week

from .conftest import WEEK_36, WEEK_37

# A Wednesday of week 38: week 37's figure is shown this week, week 36's was last week.
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
SENSOR = "sensor.thl_influenssa_ita_uusimaa"
W36 = Week(2026, 36, WEEK_36)
W37 = Week(2026, 37, WEEK_37)
HOUR = timedelta(hours=1)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Replaces the shared one: the recorder must be set up before hass."""


async def record(hass: HomeAssistant, rows: list[tuple[datetime, float]]) -> None:
    """Hourly statistics as the recorder would have compiled them."""
    if not rows:
        return
    metadata = StatisticMetaData(
        source="recorder",
        statistic_id=SENSOR,
        name=None,
        unit_of_measurement=None,
        unit_class=None,
        mean_type=StatisticMeanType.ARITHMETIC,
        has_sum=False,
    )
    async_import_statistics(hass, metadata, [StatisticData(start=start, mean=value, min=value, max=value) for start, value in rows])
    await async_wait_recording_done(hass)


async def stored(hass: HomeAssistant) -> list[tuple[datetime, float]]:
    # The recorder's own wait returns while it still runs the task it took off its queue.
    await async_wait_recording_done(hass)
    found = await get_instance(hass).async_add_executor_job(
        statistics_during_period, hass, datetime(2000, 1, 1, tzinfo=UTC), None, {SENSOR}, "hour", None, {"mean"}
    )
    return [(datetime.fromtimestamp(row["start"], UTC), row["mean"]) for row in found.get(SENSOR, [])]


# W42 and W11 are shown in a week with a clock change in Helsinki, 169 hours in autumn and 167 in spring. W12 is shown in
# the week after W11's.
W42 = Week(2026, 42, "")
W11 = Week(2027, 11, "")
W12 = Week(2027, 12, "")
AFTER_AUTUMN = datetime(2026, 10, 28, 9, 0, tzinfo=UTC)
AFTER_SPRING = datetime(2027, 4, 7, 9, 0, tzinfo=UTC)

# Each case: the time, THL's figures, the hourly rows before as (week, hour of the week it is shown in, figure), and
# the rows after.
CASES = {
    "an empty week gets one row at its start": (NOW, [(W36, 4.0), (W37, 5.0)], [], [(W36, 0, 4.0), (W37, 0, 5.0)]),
    "a week whose every row holds the figure is left alone": (
        NOW,
        [(W36, 4.0)],
        [(W36, 0, 4.0), (W36, 1, 4.0), (W36, 2, 4.0)],
        [(W36, 0, 4.0), (W36, 1, 4.0), (W36, 2, 4.0)],
    ),
    "a week the sensor began with the week before's figure gets the figure in every row": (
        NOW,
        [(W36, 4.0)],
        [(W36, 0, 3.0), (W36, 1, 3.0), (W36, 2, 4.0)],
        [(W36, 0, 4.0), (W36, 1, 4.0), (W36, 2, 4.0)],
    ),
    "a week THL has corrected since gets the corrected figure in every row": (
        NOW,
        [(W36, 4.0)],
        [(W36, 0, 2.0), (W36, 1, 2.0), (W36, 2, 2.0)],
        [(W36, 0, 4.0), (W36, 1, 4.0), (W36, 2, 4.0)],
    ),
    "a week imported as one row gets the corrected figure": (NOW, [(W36, 4.0)], [(W36, 0, 2.0)], [(W36, 0, 4.0)]),
    "the hours missing from a week stay missing": (
        NOW,
        [(W36, 4.0)],
        [(W36, 0, 2.0), (W36, 5, 2.0), (W36, 100, 2.0)],
        [(W36, 0, 4.0), (W36, 5, 4.0), (W36, 100, 4.0)],
    ),
    "the week being shown gets the figure in the hours recorded so far": (
        NOW,
        [(W37, 5.0)],
        [(W37, 0, 4.0), (W37, 1, 4.0), (W37, 2, 5.0)],
        [(W37, 0, 5.0), (W37, 1, 5.0), (W37, 2, 5.0)],
    ),
    "an hour the recorder compiled in the last two hours gets the figure too": (
        NOW,
        [(W37, 5.0)],
        [(W37, 0, 4.0), (W37, 59, 4.0)],
        [(W37, 0, 5.0), (W37, 59, 5.0)],
    ),
    "a week without a figure is left alone": (NOW, [(W36, None), (W37, None)], [(W36, 0, 2.0)], [(W36, 0, 2.0)]),
    "the last hour of a week of 169 hours gets the figure": (
        AFTER_AUTUMN,
        [(W42, 4.0)],
        [(W42, 0, 2.0), (W42, 168, 2.0)],
        [(W42, 0, 4.0), (W42, 168, 4.0)],
    ),
    "a week wrong only in its 169th hour gets the figure": (
        AFTER_AUTUMN,
        [(W42, 4.0)],
        [(W42, 0, 4.0), (W42, 168, 2.0)],
        [(W42, 0, 4.0), (W42, 168, 4.0)],
    ),
    "the week after one of 167 hours, wrong only in its first hour, gets its own figure": (
        AFTER_SPRING,
        [(W11, 4.0), (W12, 5.0)],
        [(W11, 0, 4.0), (W11, 166, 4.0), (W12, 0, 4.0)],
        [(W11, 0, 4.0), (W11, 166, 4.0), (W12, 0, 5.0)],
    ),
    "a week of 167 hours ends where the next one starts": (
        AFTER_SPRING,
        [(W11, 4.0), (W12, 5.0)],
        [(W11, 0, 2.0), (W11, 166, 2.0), (W12, 0, 5.0)],
        [(W11, 0, 4.0), (W11, 166, 4.0), (W12, 0, 5.0)],
    ),
}


def at(rows: list[tuple[Week, int, float]]) -> list[tuple[datetime, float]]:
    """The rows' hours, worked out in the test, once Home Assistant's time zone is set."""
    return [(shown_from(week) + hour * HOUR, value) for week, hour, value in rows]


@pytest.mark.parametrize(("now", "figures", "before", "after"), CASES.values(), ids=CASES.keys())
async def test_each_week_holds_thls_figure(
    recorder_mock,
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    now: datetime,
    figures: list[tuple[Week, float | None]],
    before: list[tuple[Week, int, float]],
    after: list[tuple[Week, int, float]],
) -> None:
    await hass.config.async_set_time_zone("Europe/Helsinki")
    freezer.move_to(now)
    await record(hass, at(before))

    await async_write_history(hass, [(SENSOR, None, figures)])

    assert await stored(hass) == at(after)


async def test_no_row_is_added_to_an_hour_the_recorder_has_not_compiled(
    recorder_mock, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    # Half an hour into the week week 37's figure is shown in.
    freezer.move_to(shown_from(W37) + timedelta(minutes=30))

    await async_write_history(hass, [(SENSOR, None, [(W36, 4.0), (W37, 5.0)])])

    assert await stored(hass) == [(shown_from(W36), 4.0)]


@pytest.mark.parametrize(("unit", "expected"), [("%", "unitless"), (None, "unitless"), ("per 100 000", None)])
async def test_the_unit_class_is_the_one_the_recorder_gives(
    recorder_mock, hass: HomeAssistant, freezer: FrozenDateTimeFactory, unit: str | None, expected: str | None
) -> None:
    freezer.move_to(NOW)

    await async_write_history(hass, [(SENSOR, unit, [(W36, 4.0)])])
    await async_wait_recording_done(hass)

    metadata = await get_instance(hass).async_add_executor_job(lambda: get_metadata(hass, statistic_ids={SENSOR}))
    assert metadata[SENSOR][1]["unit_class"] == expected
