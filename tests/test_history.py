"""Writing past weeks into the statistics of new sensors."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, statistics_during_period
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl.const import CONF_HISTORY_IMPORTED
from custom_components.thl.history import shown_from
from custom_components.thl.statistics import Week

from .conftest import INFLUENZA, WEEK_36, WEEK_37, thl_entry

# A Wednesday of week 38, so the last finished week is 37.
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
COUNTY = "sensor.thl_influenssa_ita_uusimaa"
COUNTY_INCIDENCE = "sensor.thl_influenssa_ita_uusimaa_incidence"
WHOLE_COUNTRY = "sensor.thl_influenssa"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Replaces the shared one: the recorder must be set up before hass, so each test asks in that order."""


async def stored(hass: HomeAssistant, statistic_id: str) -> list[tuple[float, float]]:
    """The start and mean of each row of a sensor's statistics."""
    await hass.async_block_till_done()
    await get_instance(hass).async_block_till_done()
    await hass.async_block_till_done()
    found = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        datetime(2000, 1, 1, tzinfo=UTC),
        None,
        {statistic_id},
        "hour",
        None,
        {"mean"},
    )
    return [(row["start"], row["mean"]) for row in found.get(statistic_id, [])]


def start_of(week: int) -> float:
    return shown_from(Week(2026, week, "")).timestamp()


async def test_a_new_sensor_gets_the_past_weeks(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await stored(hass, COUNTY) == [(start_of(36), 4.0), (start_of(37), 5.0)], (
        "each week from the start of the week after, when the sensor would have shown it"
    )
    assert await stored(hass, COUNTY_INCIDENCE) == [(start_of(36), 3.8), (start_of(37), 4.7)]
    [subentry] = entry.subentries.values()
    assert subentry.data[CONF_HISTORY_IMPORTED] is True, "the next start doesn't ask the recorder again"


async def test_a_sensor_with_statistics_of_its_own_is_left_alone(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    # The whole country's sensor has been running since 1.x and has recorded its own.
    recorded = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
    async_import_statistics(
        hass,
        StatisticMetaData(
            source="recorder",
            statistic_id=WHOLE_COUNTRY,
            name=None,
            unit_of_measurement=None,
            unit_class=None,
            mean_type=StatisticMeanType.ARITHMETIC,
            has_sum=False,
        ),
        [StatisticData(start=recorded, mean=42.0, min=42.0, max=42.0)],
    )
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await stored(hass, WHOLE_COUNTRY) == [(recorded.timestamp(), 42.0)]
    assert len(await stored(hass, COUNTY)) == 2, "the new county sensors still get theirs"


async def test_nothing_is_written_once_the_past_has_been_given(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    [subentry] = entry.subentries.values()
    hass.config_entries.async_update_subentry(entry, subentry, data={**subentry.data, CONF_HISTORY_IMPORTED: True})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await stored(hass, COUNTY) == []


async def test_weeks_are_shown_from_the_start_of_the_week_after(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("Europe/Helsinki")

    assert shown_from(Week(2026, 37, WEEK_37)) == datetime(2026, 9, 13, 21, 0, tzinfo=UTC), (
        "Monday 14 September at midnight in Helsinki"
    )
    assert shown_from(Week(2026, 36, WEEK_36)) == datetime(2026, 9, 6, 21, 0, tzinfo=UTC)
