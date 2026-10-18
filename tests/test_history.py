"""Writing past weeks into the statistics of sensors."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import StatisticData, StatisticMeanType, StatisticMetaData
from homeassistant.components.recorder.statistics import async_import_statistics, statistics_during_period
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.thl import history
from custom_components.thl.history import shown_from
from custom_components.thl.statistics import Week

from .conftest import ADENOVIRUS, DIMENSIONS_FI_URL, INFLUENZA, WEEK_36, WEEK_37, thl_entry

# A Wednesday of week 38, so the last finished week is 37.
NOW = datetime(2026, 9, 16, 9, 0, tzinfo=UTC)
COUNTY = "sensor.thl_influenssa_ita_uusimaa"
COUNTY_INCIDENCE = "sensor.thl_influenssa_ita_uusimaa_incidence"
WHOLE_COUNTRY = "sensor.thl_influenssa"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> None:
    """Replaces the shared one: the recorder must be set up before hass, so each test asks in that order."""


async def stored(hass: HomeAssistant, statistic_id: str) -> list[tuple[float, float]]:
    """The start and mean of each row of a sensor's statistics, once the past has been written in the background."""
    await hass.async_block_till_done(wait_background_tasks=True)
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


async def test_the_recorder_is_asked_once_for_each_subentry(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"), (ADENOVIRUS, "Adenovirus"), ili=True)
    with patch.object(history, "statistics_during_period", wraps=statistics_during_period) as asked:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert asked.call_count == 3, "not once for each of the sensors"


async def test_a_running_sensor_keeps_what_it_recorded_and_gets_the_weeks_it_has_nothing_for(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    # The whole country's sensor has been running since week 37, when week 36's figure was shown.
    recorded = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
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

    rows = await stored(hass, WHOLE_COUNTRY)
    assert (recorded.timestamp(), 42.0) in rows, "what it recorded is kept"
    assert start_of(36) not in [start for start, _ in rows], "the week it recorded is not written over"
    assert start_of(37) in [start for start, _ in rows], "the week it has nothing for is filled in"
    assert len(await stored(hass, COUNTY)) == 2, "the new county sensors get theirs"


async def test_a_sensor_enabled_later_gets_its_past(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        "thl",
        f"thl_{INFLUENZA}_ita-uudenmaan_hyvinvointialue",
        suggested_object_id="thl_influenssa_ita_uusimaa",
        config_entry=entry,
        config_subentry_id=next(iter(entry.subentries)),
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    whole_country = await stored(hass, WHOLE_COUNTRY)
    assert await stored(hass, COUNTY) == [], "a disabled sensor isn't added"

    registry.async_update_entity(COUNTY, disabled_by=None)
    assert await hass.config_entries.async_reload(entry.entry_id)

    assert await stored(hass, COUNTY) == [(start_of(36), 4.0), (start_of(37), 5.0)]
    assert await stored(hass, WHOLE_COUNTRY) == whole_country, "nothing is written twice"


async def test_the_past_is_written_once_thl_can_be_read(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    freezer.move_to(NOW)
    answers = list(aioclient_mock._mocks)
    aioclient_mock.clear_requests()
    aioclient_mock.get(DIMENSIONS_FI_URL, status=503)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(COUNTY).state == STATE_UNAVAILABLE

    aioclient_mock.clear_requests()
    aioclient_mock._mocks.extend(answers)
    freezer.tick(timedelta(minutes=2))
    await entry.runtime_data.coordinators[next(iter(entry.subentries))].async_refresh()

    assert len(await stored(hass, COUNTY)) == 2


async def test_a_failing_recorder_does_not_keep_the_sensors_away(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    freezer.move_to(NOW)
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    with patch.object(history, "statistics_during_period", side_effect=RuntimeError("the database is gone")):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get(COUNTY).state == "5"
    assert "Writing the past weeks of THL Influenssa into the statistics failed" in caplog.text


async def test_the_hours_the_recorder_has_not_compiled_yet_are_left_to_it(
    recorder_mock,
    enable_custom_integrations,
    hass: HomeAssistant,
    thl: AiohttpClientMocker,
    freezer: FrozenDateTimeFactory,
) -> None:
    # Half an hour into week 38, which week 37's figure is shown from: the recorder compiles that hour itself.
    freezer.move_to(shown_from(Week(2026, 37, WEEK_37)) + timedelta(minutes=30))
    entry = thl_entry(hass, (INFLUENZA, "Influenssa"))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await stored(hass, COUNTY) == [(start_of(36), 4.0)]


async def test_weeks_are_shown_from_the_start_of_the_week_after(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone("Europe/Helsinki")

    assert shown_from(Week(2026, 37, WEEK_37)) == datetime(2026, 9, 13, 21, 0, tzinfo=UTC), "Monday 14 September at midnight in Helsinki"
    assert shown_from(Week(2026, 36, WEEK_36)) == datetime(2026, 9, 6, 21, 0, tzinfo=UTC)
